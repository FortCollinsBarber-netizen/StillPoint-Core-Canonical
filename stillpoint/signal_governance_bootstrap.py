"""Bootstrap supporting Claim Envelopes for Signal governance.

This module creates epistemic standing records only. It never creates a standing
delegation, execution warrant, ActionRequest, credential, or external effect.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .signal_governance import (
    CEO_ISSUER,
    SCHEMA as GOVERNANCE_SCHEMA,
    SignalGovernanceError,
    SignalGovernanceSpec,
)

DRAFT_SCHEMA = "stillpoint.signal-governance-draft.v1"
PERMITTED_USE = "support_signal_standing_delegation"


def _canon(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _sha(v: Any) -> str:
    return hashlib.sha256(_canon(v).encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _nested(facts: dict[str, Any], *parts: str):
    cur: Any = facts
    for part in parts:
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


@dataclass(frozen=True)
class BootstrapPlan:
    draft_sha256: str
    governance_spec: SignalGovernanceSpec
    claims: list[dict[str, Any]]
    envelopes: list[dict[str, Any]]

    @property
    def governance_sha256(self) -> str:
        return self.governance_spec.digest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "draft_sha256": self.draft_sha256,
            "governance_sha256": self.governance_sha256,
            "governance_spec": self.governance_spec.canonical_dict(),
            "claims": self.claims,
            "envelopes": self.envelopes,
        }


def build_plan(raw: dict[str, Any]) -> BootstrapPlan:
    if not isinstance(raw, dict) or raw.get("schema") != DRAFT_SCHEMA:
        raise SignalGovernanceError(f"draft schema must be {DRAFT_SCHEMA}")
    if str(raw.get("issuer") or "") != CEO_ISSUER:
        raise SignalGovernanceError(f"issuer must be {CEO_ISSUER}")
    if raw.get("claim_envelope_ids"):
        raise SignalGovernanceError("draft must not preassign claim_envelope_ids")

    facts_snapshot = raw.get("facts_snapshot")
    facts = facts_snapshot.get("facts") if isinstance(facts_snapshot, dict) else None
    if not isinstance(facts, dict):
        raise SignalGovernanceError("facts_snapshot.facts required")
    account = str(raw.get("gmail_account") or "").strip().lower()
    spec_id = str(raw.get("spec_id") or "").strip()
    if _nested(facts, "signal_email", "account") != account:
        raise SignalGovernanceError("facts_snapshot must bind exact signal_email.account")
    if _nested(facts, "signal_governance", "spec_id") != spec_id:
        raise SignalGovernanceError("facts_snapshot must bind exact signal_governance.spec_id")
    if _nested(facts, "signal_governance", "policy_current") is not True:
        raise SignalGovernanceError("facts_snapshot must state signal_governance.policy_current=true")

    draft_sha = _sha(raw)
    suffix = draft_sha[:16]
    claim_ids = {
        "mailbox": f"signal-claim-mailbox-{suffix}",
        "policy": f"signal-claim-policy-{suffix}",
        "standing": f"signal-claim-standing-{suffix}",
    }
    envelope_ids = {k: f"signal-envelope-{k}-{suffix}" for k in claim_ids}

    gov_raw = dict(raw)
    gov_raw["schema"] = GOVERNANCE_SCHEMA
    gov_raw["claim_envelope_ids"] = [envelope_ids["mailbox"], envelope_ids["policy"], envelope_ids["standing"]]
    governance = SignalGovernanceSpec.from_dict(gov_raw)

    asserted = str(raw.get("valid_from") or _now())
    effective_to = str(raw.get("review_by") or "")
    base_provenance = {
        "source": "signal_governance_bootstrap",
        "draft_sha256": draft_sha,
        "governance_sha256": governance.digest(),
        "spec_id": governance.spec_id,
    }
    claims = [
        {
            "claim_id": claim_ids["mailbox"], "subject": "office:signal", "predicate": "operates_mailbox",
            "value": governance.gmail_account, "domain": "operational", "source": CEO_ISSUER,
            "time_asserted": asserted, "effective_from": governance.valid_from, "effective_to": effective_to,
            "confidence": 1.0, "status": "active", "provenance": base_provenance,
        },
        {
            "claim_id": claim_ids["policy"], "subject": "office:signal", "predicate": "governance_spec",
            "value": governance.spec_id, "domain": "operational", "source": CEO_ISSUER,
            "time_asserted": asserted, "effective_from": governance.valid_from, "effective_to": effective_to,
            "confidence": 1.0, "status": "active", "provenance": base_provenance,
        },
        {
            "claim_id": claim_ids["standing"], "subject": "office:signal", "predicate": "governance_policy_current",
            "value": True, "domain": "operational", "source": CEO_ISSUER,
            "time_asserted": asserted, "effective_from": governance.valid_from, "effective_to": effective_to,
            "confidence": 1.0, "status": "active", "provenance": base_provenance,
        },
    ]
    reach = {
        "available_sources": ["CEO governance draft", "finite continuation facts snapshot"],
        "unavailable_sources": ["facts outside configured StillPoint/Gmail evidence channels"],
        "observed_variables": ["mailbox identity", "policy identity", "policy-current assertion"],
        "inferred_variables": [],
        "model_boundaries": ["does not establish recipient intent, delivery, legal authority, or financial authority"],
        "blind_spots": ["external state not represented in the continuation facts snapshot"],
    }
    common = {
        "domain": "communications",
        "purpose": "Support bounded Signal standing-delegation evaluation only",
        "epistemic_reach": reach,
        "permitted_uses": [PERMITTED_USE],
        "prohibited_uses": ["mint_warrant", "send_email", "publish", "spend", "sign"],
        "correction_routes": ["CEO policy revision", "new evidence", "release-gate review"],
        "release_conditions": list(governance.release_conditions),
        "reentry_requirements": ["new current evidence", "new or revalidated CEO governance standing"],
        "memory_policy": {"purposes": ["history", "accountability", "audit"], "retain_until": None, "operational_reauthorization": False},
        "operational": True, "status": "active",
    }
    envelopes = [
        dict(common, envelope_id=envelope_ids["mailbox"], claim_id=claim_ids["mailbox"], continuation_conditions=[{"key":"signal_email.account","operator":"eq","expected":governance.gmail_account,"note":"exact mailbox identity must remain current"}]),
        dict(common, envelope_id=envelope_ids["policy"], claim_id=claim_ids["policy"], continuation_conditions=[{"key":"signal_governance.spec_id","operator":"eq","expected":governance.spec_id,"note":"exact governance policy identity must remain current"}]),
        dict(common, envelope_id=envelope_ids["standing"], claim_id=claim_ids["standing"], continuation_conditions=[{"key":"signal_governance.policy_current","operator":"eq","expected":True,"note":"governance standing must remain affirmatively current"}]),
    ]
    return BootstrapPlan(draft_sha, governance, claims, envelopes)


class SignalGovernanceBootstrapper:
    def __init__(self, db): self.db = db

    def preview(self, raw: dict[str, Any]) -> dict[str, Any]:
        plan = build_plan(raw); c=self.db._connection(); conflicts=[]; existing=[]
        for claim in plan.claims:
            row=c.execute("select predicate,value_json,status from temporal_claims where claim_id=?",(claim["claim_id"],)).fetchone()
            if row: existing.append(claim["claim_id"])
        for env in plan.envelopes:
            row=c.execute("select claim_id,status from temporal_claim_envelopes where envelope_id=?",(env["envelope_id"],)).fetchone()
            if row and row["claim_id"]!=env["claim_id"]: conflicts.append(env["envelope_id"])
        return {"draft_sha256":plan.draft_sha256,"governance_sha256":plan.governance_sha256,"governance_spec":plan.governance_spec.canonical_dict(),"claim_envelope_ids":[x["envelope_id"] for x in plan.envelopes],"existing_claims":existing,"conflicts":conflicts,"ready_to_seed":not conflicts,"authority_change":False}

    def seed(self, raw: dict[str, Any], *, expected_draft_sha256: str, ceo_confirmed: bool) -> dict[str, Any]:
        plan=build_plan(raw)
        if not ceo_confirmed: raise SignalGovernanceError("explicit CEO confirmation required")
        if expected_draft_sha256 != plan.draft_sha256: raise SignalGovernanceError("CEO confirmation digest does not match exact draft")
        preview=self.preview(raw)
        if not preview["ready_to_seed"]: raise SignalGovernanceError("bootstrap conflicts: "+_canon(preview["conflicts"]))
        c=self.db._connection(); now=_now()
        try:
            c.execute("BEGIN IMMEDIATE")
            for claim in plan.claims:
                row=c.execute("select provenance_json,status from temporal_claims where claim_id=?",(claim["claim_id"],)).fetchone()
                if row:
                    prov=json.loads(row["provenance_json"] or "{}")
                    if prov.get("draft_sha256")!=plan.draft_sha256: raise SignalGovernanceError("claim id conflict")
                    continue
                c.execute("""INSERT INTO temporal_claims(claim_id,subject,predicate,value_json,domain,source,evidence_refs_json,time_observed,time_asserted,effective_from,effective_to,confidence,status,supersedes,superseded_by,review_conditions_json,provenance_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (claim["claim_id"],claim["subject"],claim["predicate"],_canon(claim["value"]),claim["domain"],claim["source"],"[]",claim["time_asserted"],claim["time_asserted"],claim["effective_from"],claim["effective_to"],claim["confidence"],claim["status"],None,None,_canon(["governance review boundary","contradictory evidence"]),_canon(claim["provenance"]),now,now))
            for env in plan.envelopes:
                row=c.execute("select claim_id,status from temporal_claim_envelopes where envelope_id=?",(env["envelope_id"],)).fetchone()
                if row:
                    if row["claim_id"]!=env["claim_id"]: raise SignalGovernanceError("envelope id conflict")
                    continue
                c.execute("""INSERT INTO temporal_claim_envelopes(envelope_id,claim_id,domain,purpose,epistemic_reach_json,permitted_uses_json,prohibited_uses_json,continuation_conditions_json,correction_routes_json,release_conditions_json,reentry_requirements_json,memory_policy_json,memory_may_reauthorize,operational,status,supersedes_envelope_id,superseded_by_envelope_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (env["envelope_id"],env["claim_id"],env["domain"],env["purpose"],_canon(env["epistemic_reach"]),_canon(env["permitted_uses"]),_canon(env["prohibited_uses"]),_canon(env["continuation_conditions"]),_canon(env["correction_routes"]),_canon(env["release_conditions"]),_canon(env["reentry_requirements"]),_canon(env["memory_policy"]),0,1,env["status"],None,None,now,now))
            c.commit()
        except Exception:
            c.rollback(); raise
        return {"seeded":True,"draft_sha256":plan.draft_sha256,"governance_sha256":plan.governance_sha256,"governance_spec":plan.governance_spec.canonical_dict(),"claim_envelope_ids":[x["envelope_id"] for x in plan.envelopes]}
