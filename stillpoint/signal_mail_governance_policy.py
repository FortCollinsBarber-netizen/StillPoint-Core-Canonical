"""Provider-neutral CEO governance provisioning for Signal mail.

Patch 032 supersedes the Gmail-specific governance installer for the Apple-first
Signal path. Authority binds to one exact MailboxIdentity: provider + account +
jurisdiction. Bootstrap creates epistemic claims/envelopes only; apply creates
one standing delegation and one matching event trigger only after explicit CEO
confirmation of the exact canonical policy digest.
"""
from __future__ import annotations

import hashlib, json, os, tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .mail_contracts import MailboxIdentity
from .signal_mail_governance import MailboxGovernanceSpec, SAFE_AUTONOMOUS_CLASSIFICATIONS
from .temporal.envelope import ContinuationCondition, ConditionOperator

CEO_ISSUER = "CEO:Robert Emmanuel LaDay"
POLICY_SCHEMA = "stillpoint.signal-mail-governance.v1"
DRAFT_SCHEMA = "stillpoint.signal-mail-governance-draft.v1"
PERMITTED_USE = "standing_delegation_evaluation"

class SignalMailGovernanceError(RuntimeError):
    pass

def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)

def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value).encode("utf-8")).hexdigest()

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _parse(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception as exc:
        raise SignalMailGovernanceError(f"invalid governance timestamp: {value!r}") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise SignalMailGovernanceError("governance timestamps must be timezone-aware")
    return dt.astimezone(timezone.utc)

def _conditions(raw) -> list[ContinuationCondition]:
    out=[]
    for x in raw or []:
        out.append(ContinuationCondition(
            key=str(x["key"]),
            operator=ConditionOperator(str(x.get("operator") or "eq")),
            expected=x.get("expected"),
            note=str(x.get("note") or ""),
        ))
    return out

def _nested(value: dict[str,Any], *path: str):
    cur: Any = value
    for part in path:
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur

@dataclass(frozen=True)
class SignalMailGovernanceSpec:
    spec_id: str
    identity: MailboxIdentity
    delegation_id: str
    trigger_id: str
    policy_basis: str
    purpose: str
    claim_envelope_ids: list[str]
    allowed_classifications: list[str]
    continuation_conditions: list[ContinuationCondition]
    exclusions: list[str]
    release_conditions: list[str]
    valid_from: str
    review_by: str
    trigger_valid_from: str
    trigger_review_by: str
    facts_snapshot: dict[str,Any]
    issuer: str = CEO_ISSUER
    schema: str = POLICY_SCHEMA

    @classmethod
    def from_dict(cls, raw: dict[str,Any]):
        if not isinstance(raw, dict) or raw.get("schema") != POLICY_SCHEMA:
            raise SignalMailGovernanceError(f"schema must be {POLICY_SCHEMA}")
        if str(raw.get("issuer") or "") != CEO_ISSUER:
            raise SignalMailGovernanceError(f"issuer must be {CEO_ISSUER}")
        box = raw.get("mailbox")
        if not isinstance(box, dict):
            raise SignalMailGovernanceError("mailbox object required")
        try:
            identity = MailboxIdentity(str(box.get("provider") or ""), str(box.get("account") or ""), str(box.get("jurisdiction") or ""))
        except Exception as exc:
            raise SignalMailGovernanceError(str(exc)) from exc
        required={k:str(raw.get(k) or "").strip() for k in ("spec_id","delegation_id","trigger_id","policy_basis","purpose")}
        if any(not x for x in required.values()):
            raise SignalMailGovernanceError("spec_id, delegation_id, trigger_id, policy_basis, and purpose required")
        env=[str(x).strip() for x in raw.get("claim_envelope_ids") or [] if str(x).strip()]
        if not env:
            raise SignalMailGovernanceError("claim_envelope_ids required")
        classes=[str(x).strip() for x in raw.get("allowed_classifications") or [] if str(x).strip()]
        if not classes or not set(classes).issubset(SAFE_AUTONOMOUS_CLASSIFICATIONS):
            raise SignalMailGovernanceError("allowed_classifications must be a non-empty subset of safe routine classes")
        cont=_conditions(raw.get("continuation_conditions"))
        if not cont:
            raise SignalMailGovernanceError("continuation_conditions required")
        exclusions=[str(x).strip() for x in raw.get("exclusions") or [] if str(x).strip()]
        releases=[str(x).strip() for x in raw.get("release_conditions") or [] if str(x).strip()]
        if not exclusions or not releases:
            raise SignalMailGovernanceError("exclusions and release_conditions required")
        vf=str(raw.get("valid_from") or ""); rb=str(raw.get("review_by") or "")
        tvf=str(raw.get("trigger_valid_from") or vf); trb=str(raw.get("trigger_review_by") or rb)
        if _parse(rb) <= _parse(vf):
            raise SignalMailGovernanceError("review_by must follow valid_from")
        if _parse(trb) <= _parse(tvf) or _parse(tvf) < _parse(vf) or _parse(trb) > _parse(rb):
            raise SignalMailGovernanceError("trigger authority must fit inside delegation review interval")
        snap=raw.get("facts_snapshot")
        if not isinstance(snap,dict) or not isinstance(snap.get("facts"),dict):
            raise SignalMailGovernanceError("facts_snapshot with facts object required")
        observed=str(snap.get("observed_at") or ""); until=str(snap.get("valid_until") or "")
        if not observed or not until or _parse(until) <= _parse(observed) or _parse(until) > _parse(rb):
            raise SignalMailGovernanceError("facts_snapshot must have finite validity inside review interval")
        facts=snap["facts"]
        if _nested(facts,"signal_mail","provider") != identity.provider:
            raise SignalMailGovernanceError("facts_snapshot must bind exact signal_mail.provider")
        if _nested(facts,"signal_mail","account") != identity.account:
            raise SignalMailGovernanceError("facts_snapshot must bind exact signal_mail.account")
        if _nested(facts,"signal_mail","jurisdiction") != identity.jurisdiction:
            raise SignalMailGovernanceError("facts_snapshot must bind exact signal_mail.jurisdiction")
        if _nested(facts,"signal_governance","spec_id") != required["spec_id"]:
            raise SignalMailGovernanceError("facts_snapshot must bind exact signal_governance.spec_id")
        if _nested(facts,"signal_governance","policy_current") is not True:
            raise SignalMailGovernanceError("facts_snapshot must state signal_governance.policy_current=true")
        return cls(
            spec_id=required["spec_id"], identity=identity, delegation_id=required["delegation_id"],
            trigger_id=required["trigger_id"], policy_basis=required["policy_basis"], purpose=required["purpose"],
            claim_envelope_ids=env, allowed_classifications=classes, continuation_conditions=cont,
            exclusions=exclusions, release_conditions=releases, valid_from=vf, review_by=rb,
            trigger_valid_from=tvf, trigger_review_by=trb, facts_snapshot=dict(snap), issuer=CEO_ISSUER,
        )

    def standing_spec(self) -> MailboxGovernanceSpec:
        return MailboxGovernanceSpec(
            identity=self.identity, delegation_id=self.delegation_id,
            claim_envelope_ids=list(self.claim_envelope_ids), allowed_classifications=list(self.allowed_classifications),
            continuation_conditions=list(self.continuation_conditions), exclusions=list(self.exclusions),
            release_conditions=list(self.release_conditions), valid_from=self.valid_from, review_by=self.review_by,
            policy_basis=self.policy_basis, purpose=self.purpose, issuer=self.issuer,
        )

    def execution_conditions(self) -> list[ContinuationCondition]:
        return self.standing_spec().standing().execution_conditions

    def canonical_dict(self) -> dict[str,Any]:
        return {
            "schema":self.schema,"issuer":self.issuer,"spec_id":self.spec_id,
            "mailbox":self.identity.to_dict(),"delegation_id":self.delegation_id,"trigger_id":self.trigger_id,
            "policy_basis":self.policy_basis,"purpose":self.purpose,"claim_envelope_ids":list(self.claim_envelope_ids),
            "allowed_classifications":list(self.allowed_classifications),
            "continuation_conditions":[x.to_dict() for x in self.continuation_conditions],
            "exclusions":list(self.exclusions),"release_conditions":list(self.release_conditions),
            "valid_from":self.valid_from,"review_by":self.review_by,
            "trigger_valid_from":self.trigger_valid_from,"trigger_review_by":self.trigger_review_by,
            "facts_snapshot":self.facts_snapshot,
        }

    def digest(self) -> str:
        return _sha(self.canonical_dict())

@dataclass(frozen=True)
class BootstrapPlan:
    draft_sha256: str
    governance_spec: SignalMailGovernanceSpec
    claims: list[dict[str,Any]]
    envelopes: list[dict[str,Any]]
    @property
    def governance_sha256(self): return self.governance_spec.digest()

def build_bootstrap_plan(raw: dict[str,Any]) -> BootstrapPlan:
    if not isinstance(raw,dict) or raw.get("schema") != DRAFT_SCHEMA:
        raise SignalMailGovernanceError(f"draft schema must be {DRAFT_SCHEMA}")
    if str(raw.get("issuer") or "") != CEO_ISSUER:
        raise SignalMailGovernanceError(f"issuer must be {CEO_ISSUER}")
    if raw.get("claim_envelope_ids"):
        raise SignalMailGovernanceError("draft must not preassign claim_envelope_ids")
    draft_sha=_sha(raw); suffix=draft_sha[:16]
    claim_ids={k:f"signal-mail-claim-{k}-{suffix}" for k in ("mailbox","policy","standing")}
    env_ids={k:f"signal-mail-envelope-{k}-{suffix}" for k in claim_ids}
    policy=dict(raw); policy["schema"]=POLICY_SCHEMA; policy["claim_envelope_ids"]=[env_ids["mailbox"],env_ids["policy"],env_ids["standing"]]
    spec=SignalMailGovernanceSpec.from_dict(policy)
    asserted=spec.valid_from; effective_to=spec.review_by
    provenance={"source":"signal_mail_governance_bootstrap","draft_sha256":draft_sha,"governance_sha256":spec.digest(),"spec_id":spec.spec_id,"mailbox":spec.identity.to_dict()}
    subject=spec.identity.authority_subject
    claims=[
        {"claim_id":claim_ids["mailbox"],"subject":subject,"predicate":"mailbox_identity","value":spec.identity.to_dict()},
        {"claim_id":claim_ids["policy"],"subject":subject,"predicate":"governance_spec","value":spec.spec_id},
        {"claim_id":claim_ids["standing"],"subject":subject,"predicate":"governance_policy_current","value":True},
    ]
    for claim in claims:
        claim.update({"domain":"operational","source":CEO_ISSUER,"time_asserted":asserted,"effective_from":spec.valid_from,"effective_to":effective_to,"confidence":1.0,"status":"active","provenance":provenance})
    reach={
        "available_sources":["CEO governance draft","finite continuation facts snapshot","configured mailbox identity"],
        "unavailable_sources":["external state outside configured StillPoint mail/evidence channels"],
        "observed_variables":["provider","mailbox account","jurisdiction","policy identity","policy-current assertion"],
        "inferred_variables":[],"model_boundaries":["does not establish recipient intent, delivery, legal authority, or financial authority"],
        "blind_spots":["external state not represented in the continuation facts snapshot"],
    }
    common={
        "domain":"communications","purpose":"Support bounded Signal standing-delegation evaluation only",
        "epistemic_reach":reach,"permitted_uses":[PERMITTED_USE],
        "prohibited_uses":["mint_warrant","send_email","publish","spend","sign"],
        "correction_routes":["CEO policy revision","new evidence","release-gate review"],
        "release_conditions":list(spec.release_conditions),
        "reentry_requirements":["new current evidence","new or revalidated CEO governance standing"],
        "memory_policy":{"purposes":["history","accountability","audit"],"retain_until":None,"operational_reauthorization":False},
        "operational":True,"status":"active",
    }
    envelopes=[
        dict(common,envelope_id=env_ids["mailbox"],claim_id=claim_ids["mailbox"],continuation_conditions=[
            {"key":"signal_mail.provider","operator":"eq","expected":spec.identity.provider,"note":"exact provider must remain current"},
            {"key":"signal_mail.account","operator":"eq","expected":spec.identity.account,"note":"exact mailbox must remain current"},
            {"key":"signal_mail.jurisdiction","operator":"eq","expected":spec.identity.jurisdiction,"note":"exact jurisdiction must remain current"},
        ]),
        dict(common,envelope_id=env_ids["policy"],claim_id=claim_ids["policy"],continuation_conditions=[{"key":"signal_governance.spec_id","operator":"eq","expected":spec.spec_id,"note":"exact policy identity must remain current"}]),
        dict(common,envelope_id=env_ids["standing"],claim_id=claim_ids["standing"],continuation_conditions=[{"key":"signal_governance.policy_current","operator":"eq","expected":True,"note":"governance standing must remain affirmatively current"}]),
    ]
    return BootstrapPlan(draft_sha,spec,claims,envelopes)

class SignalMailGovernanceProvisioner:
    def __init__(self, db): self.db=db

    def preview_seed(self, raw: dict[str,Any]) -> dict[str,Any]:
        plan=build_bootstrap_plan(raw); c=self.db._connection(); conflicts=[]; existing=[]
        for claim in plan.claims:
            row=c.execute("select provenance_json from temporal_claims where claim_id=?",(claim["claim_id"],)).fetchone()
            if row: existing.append(claim["claim_id"])
        for env in plan.envelopes:
            row=c.execute("select claim_id from temporal_claim_envelopes where envelope_id=?",(env["envelope_id"],)).fetchone()
            if row and row["claim_id"] != env["claim_id"]: conflicts.append(env["envelope_id"])
        return {"draft_sha256":plan.draft_sha256,"governance_sha256":plan.governance_sha256,"governance_spec":plan.governance_spec.canonical_dict(),"claim_envelope_ids":[x["envelope_id"] for x in plan.envelopes],"existing_claims":existing,"conflicts":conflicts,"ready_to_seed":not conflicts,"authority_change":False}

    def seed(self, raw: dict[str,Any], *, expected_draft_sha256: str, ceo_confirmed: bool) -> dict[str,Any]:
        plan=build_bootstrap_plan(raw)
        if not ceo_confirmed: raise SignalMailGovernanceError("explicit CEO confirmation required")
        if expected_draft_sha256 != plan.draft_sha256: raise SignalMailGovernanceError("CEO confirmation digest does not match exact draft")
        preview=self.preview_seed(raw)
        if not preview["ready_to_seed"]: raise SignalMailGovernanceError("bootstrap conflicts: "+_canon(preview["conflicts"]))
        c=self.db._connection(); now=_now()
        try:
            c.execute("BEGIN IMMEDIATE")
            for claim in plan.claims:
                row=c.execute("select provenance_json from temporal_claims where claim_id=?",(claim["claim_id"],)).fetchone()
                if row:
                    prov=json.loads(row["provenance_json"] or "{}")
                    if prov.get("draft_sha256") != plan.draft_sha256: raise SignalMailGovernanceError("claim id conflict")
                    continue
                c.execute("""INSERT INTO temporal_claims(claim_id,subject,predicate,value_json,domain,source,evidence_refs_json,time_observed,time_asserted,effective_from,effective_to,confidence,status,supersedes,superseded_by,review_conditions_json,provenance_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (claim["claim_id"],claim["subject"],claim["predicate"],_canon(claim["value"]),claim["domain"],claim["source"],"[]",claim["time_asserted"],claim["time_asserted"],claim["effective_from"],claim["effective_to"],claim["confidence"],claim["status"],None,None,_canon(["governance review boundary","contradictory evidence"]),_canon(claim["provenance"]),now,now))
            for env in plan.envelopes:
                row=c.execute("select claim_id from temporal_claim_envelopes where envelope_id=?",(env["envelope_id"],)).fetchone()
                if row:
                    if row["claim_id"] != env["claim_id"]: raise SignalMailGovernanceError("envelope id conflict")
                    continue
                c.execute("""INSERT INTO temporal_claim_envelopes(envelope_id,claim_id,domain,purpose,epistemic_reach_json,permitted_uses_json,prohibited_uses_json,continuation_conditions_json,correction_routes_json,release_conditions_json,reentry_requirements_json,memory_policy_json,memory_may_reauthorize,operational,status,supersedes_envelope_id,superseded_by_envelope_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (env["envelope_id"],env["claim_id"],env["domain"],env["purpose"],_canon(env["epistemic_reach"]),_canon(env["permitted_uses"]),_canon(env["prohibited_uses"]),_canon(env["continuation_conditions"]),_canon(env["correction_routes"]),_canon(env["release_conditions"]),_canon(env["reentry_requirements"]),_canon(env["memory_policy"]),0,1,env["status"],None,None,now,now))
            c.commit()
        except Exception:
            c.rollback(); raise
        return {"seeded":True,"draft_sha256":plan.draft_sha256,"governance_sha256":plan.governance_sha256,"governance_spec":plan.governance_spec.canonical_dict(),"claim_envelope_ids":[x["envelope_id"] for x in plan.envelopes]}

    def preview_apply(self, spec: SignalMailGovernanceSpec) -> dict[str,Any]:
        c=self.db._connection(); missing=[]; former=[]; digest=spec.digest(); conflicts=[]
        for eid in spec.claim_envelope_ids:
            row=c.execute("select status from temporal_claim_envelopes where envelope_id=?",(eid,)).fetchone()
            if not row: missing.append(eid)
            elif row["status"] != "active": former.append(eid)
        d=c.execute("select policy_basis from standing_delegations where delegation_id=?",(spec.delegation_id,)).fetchone()
        t=c.execute("select metadata_json from trigger_definitions where trigger_id=?",(spec.trigger_id,)).fetchone()
        marker=f"signal_mail_governance_spec:{digest}"
        if d and marker not in str(d["policy_basis"]): conflicts.append("delegation_id_already_used_by_different_policy")
        if t:
            try: meta=json.loads(t["metadata_json"] or "{}")
            except Exception: meta={}
            if meta.get("signal_mail_governance_sha256") != digest: conflicts.append("trigger_id_already_used_by_different_policy")
        return {"spec_id":spec.spec_id,"sha256":digest,"ready_to_apply":not(missing or former or conflicts),"missing_envelopes":missing,"noncurrent_envelopes":former,"conflicts":conflicts,"existing_delegation":bool(d),"existing_trigger":bool(t),"authority_change":True}

    def apply(self, spec: SignalMailGovernanceSpec, *, facts_file: Path, expected_sha256: str, ceo_confirmed: bool) -> dict[str,Any]:
        digest=spec.digest()
        if not ceo_confirmed: raise SignalMailGovernanceError("explicit CEO confirmation required")
        if expected_sha256 != digest: raise SignalMailGovernanceError("CEO confirmation digest does not match exact governance spec")
        preview=self.preview_apply(spec)
        if not preview["ready_to_apply"]: raise SignalMailGovernanceError("governance spec is not applicable: "+_canon(preview))
        facts_file=Path(facts_file)
        if not facts_file.is_absolute() or facts_file.is_symlink(): raise SignalMailGovernanceError("facts_file must be absolute and not a symlink")
        facts_file.parent.mkdir(parents=True,exist_ok=True)
        tmp_path=Path(tempfile.mkstemp(prefix=".signal-mail-facts-",dir=facts_file.parent)[1]); tmp_path.write_text(_canon(spec.facts_snapshot)+"\n",encoding="utf-8")
        c=self.db._connection(); now=_now(); marker=f"{spec.policy_basis};signal_mail_governance_spec:{digest}"
        standing=spec.standing_spec().standing()
        try:
            try:
                c.execute("BEGIN IMMEDIATE")
                for eid in spec.claim_envelope_ids:
                    row=c.execute("select status from temporal_claim_envelopes where envelope_id=?",(eid,)).fetchone()
                    if not row or row["status"] != "active": raise SignalMailGovernanceError(f"supporting envelope changed before apply: {eid}")
                d=c.execute("select policy_basis from standing_delegations where delegation_id=?",(spec.delegation_id,)).fetchone()
                if not d:
                    c.execute("""INSERT INTO standing_delegations(delegation_id,delegate_role,issuer,policy_basis,purpose,claim_envelope_ids_json,allowed_action_types_json,continuation_conditions_json,execution_conditions_json,exclusions_json,release_conditions_json,valid_from,review_by,status,supersedes_delegation_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (standing.delegation_id,standing.delegate_role,standing.issuer,marker,standing.purpose,_canon(standing.claim_envelope_ids),_canon(standing.allowed_action_types),_canon([x.to_dict() for x in standing.continuation_conditions]),_canon([x.to_dict() for x in standing.execution_conditions]),_canon(standing.exclusions),_canon(standing.release_conditions),standing.valid_from,standing.review_by,"active",None,now,now))
                elif f"signal_mail_governance_spec:{digest}" not in str(d["policy_basis"]): raise SignalMailGovernanceError("delegation conflict during apply")
                metadata={"signal_mail_governance_spec_id":spec.spec_id,"signal_mail_governance_sha256":digest,"provider":spec.identity.provider,"account":spec.identity.account,"jurisdiction":spec.identity.jurisdiction}
                t=c.execute("select metadata_json from trigger_definitions where trigger_id=?",(spec.trigger_id,)).fetchone()
                if not t:
                    c.execute("""INSERT INTO trigger_definitions(trigger_id,owner_role,trigger_kind,source,event_type,goal_template,project,status,valid_from,review_by,next_run_at,interval_seconds,max_runs,run_count,catch_up_policy,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (spec.trigger_id,"signal","event",spec.identity.provider,"message_received",f"Handle Signal {spec.identity.provider} message {{event_id}}","signal","active",spec.trigger_valid_from,spec.trigger_review_by,None,None,None,0,"coalesce",_canon(metadata),now,now))
                else:
                    try: existing=json.loads(t["metadata_json"] or "{}")
                    except Exception: existing={}
                    if existing.get("signal_mail_governance_sha256") != digest: raise SignalMailGovernanceError("trigger conflict during apply")
                c.commit()
            except Exception:
                c.rollback(); raise
            os.replace(tmp_path,facts_file)
            return {"applied":True,"sha256":digest,"delegation_id":spec.delegation_id,"trigger_id":spec.trigger_id,"mailbox":spec.identity.to_dict(),"facts_file":str(facts_file),"reused_existing":preview["existing_delegation"] and preview["existing_trigger"]}
        finally:
            if tmp_path.exists():
                try: tmp_path.unlink()
                except Exception: pass
