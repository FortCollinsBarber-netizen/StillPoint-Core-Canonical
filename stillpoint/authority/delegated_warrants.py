"""Derive one finite execution warrant from current standing delegation.

This layer never turns standing delegation itself into external authority. It
binds a fresh, action-specific standing evaluation to one ActionRequest and one
short-lived, one-use temporal Warrant.

Call ``validate_delegated_warrant_current`` again immediately before crossing
the external dispatch boundary. That check lets revocation, review expiry, a
newer failed evaluation, or a former supporting envelope stop a warrant that
was valid when issued.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from stillpoint.temporal.action_gate import action_domain, action_subject
from stillpoint.temporal.warrants import Warrant


DEFAULT_DELEGATED_WARRANT_TTL_SECONDS = 300
DEFAULT_MAX_EVALUATION_AGE_SECONDS = 60


class DelegatedAuthorizationError(RuntimeError):
    pass


def _parse_time(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception as exc:
        raise DelegatedAuthorizationError(f"invalid authority timestamp: {value!r}") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise DelegatedAuthorizationError("authority timestamps must be timezone-aware")
    return dt.astimezone(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _artifact_binding(action_row: dict[str, Any]) -> list[dict[str, Any]]:
    items = json.loads(action_row.get("artifact_refs_json") or "[]")
    return [
        {
            "artifact_id": item.get("artifact_id"),
            "version": item.get("version", 1),
            "sha256": item.get("sha256", ""),
            "kind": item.get("kind", "other"),
        }
        for item in items
    ]


def _claim_and_evidence_ids(conn, supporting_envelope_ids: list[str]) -> tuple[list[str], list[str]]:
    claim_ids: list[str] = []
    evidence_ids: list[str] = []
    for envelope_id in supporting_envelope_ids:
        row = conn.execute(
            "SELECT claim_id,status FROM temporal_claim_envelopes WHERE envelope_id=?",
            (envelope_id,),
        ).fetchone()
        if not row or row["status"] != "active":
            raise DelegatedAuthorizationError(f"supporting envelope not current: {envelope_id}")
        claim_id = str(row["claim_id"])
        if claim_id not in claim_ids:
            claim_ids.append(claim_id)
        claim = conn.execute(
            "SELECT evidence_refs_json FROM temporal_claims WHERE claim_id=?", (claim_id,)
        ).fetchone()
        if claim and claim["evidence_refs_json"]:
            for item in json.loads(claim["evidence_refs_json"]):
                evidence_id = item.get("evidence_id") if isinstance(item, dict) else None
                if evidence_id and evidence_id not in evidence_ids:
                    evidence_ids.append(evidence_id)
    return claim_ids, evidence_ids


def _build_warrant(
    *,
    action_row: dict[str, Any],
    delegation_row,
    evaluation_row,
    claim_ids: list[str],
    evidence_ids: list[str],
    now: datetime,
    ttl_seconds: int,
) -> Warrant:
    if ttl_seconds <= 0:
        raise DelegatedAuthorizationError("delegated warrant ttl must be positive")
    action_expiry = _parse_time(action_row["expires_at"])
    review_by = _parse_time(delegation_row["review_by"])
    valid_to = min(action_expiry, review_by, now + timedelta(seconds=ttl_seconds))
    if valid_to <= now:
        raise DelegatedAuthorizationError("no positive delegated warrant interval remains")

    scope = json.loads(action_row.get("scope_json") or "[]")
    artifact_binding = _artifact_binding(action_row)
    return Warrant(
        warrant_id="",
        domain=action_domain(action_row["action_type"]),
        action_class=action_row["action_type"],
        subject=action_subject(action_row["task_id"]),
        target=action_row["target"],
        claim_ids=claim_ids,
        evidence_ids=evidence_ids,
        issuer=delegation_row["issuer"],
        policy_basis=f"standing_delegation:{delegation_row['delegation_id']}:{evaluation_row['evaluation_id']}",
        issued_at=_iso(now),
        valid_from=_iso(now),
        valid_to=_iso(valid_to),
        scope={
            "subjects": [action_subject(action_row["task_id"])],
            "targets": [action_row["target"]],
            "allowed_scope": list(scope),
            "max_actions": 1,
            "authority_revision": action_row["authority_revision"],
            "artifact_binding": artifact_binding,
            "standing_delegation_id": delegation_row["delegation_id"],
            "standing_evaluation_id": evaluation_row["evaluation_id"],
            "standing_facts_sha256": evaluation_row["facts_sha256"],
        },
        provenance={
            "source": "standing_delegation",
            "delegation_id": delegation_row["delegation_id"],
            "evaluation_id": evaluation_row["evaluation_id"],
            "action_id": action_row["id"],
            "task_id": action_row["task_id"],
            "facts_sha256": evaluation_row["facts_sha256"],
        },
    )


class DelegatedWarrantIssuer:
    def __init__(self, db):
        self.db = db

    def authorize_waiting_action(
        self,
        *,
        action_id: str,
        delegation_id: str,
        evaluation_id: str,
        now_iso: str,
        ttl_seconds: int = DEFAULT_DELEGATED_WARRANT_TTL_SECONDS,
        max_evaluation_age_seconds: int = DEFAULT_MAX_EVALUATION_AGE_SECONDS,
    ) -> Warrant:
        now = _parse_time(now_iso)
        conn = self.db._connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            action = conn.execute("SELECT * FROM action_requests WHERE id=?", (action_id,)).fetchone()
            if not action:
                raise KeyError(action_id)
            action = dict(action)
            if action["status"] != "waiting_approval":
                raise DelegatedAuthorizationError("delegated authorization requires waiting_approval action")
            if action.get("warrant_id"):
                raise DelegatedAuthorizationError("action already has a warrant")
            if action.get("approval_id"):
                raise DelegatedAuthorizationError("action already has explicit approval binding")

            delegation = conn.execute(
                "SELECT * FROM standing_delegations WHERE delegation_id=?", (delegation_id,)
            ).fetchone()
            if not delegation or delegation["status"] != "active":
                raise DelegatedAuthorizationError("standing delegation is not active")
            if now < _parse_time(delegation["valid_from"]) or now >= _parse_time(delegation["review_by"]):
                raise DelegatedAuthorizationError("standing delegation is outside current review interval")
            allowed_actions = json.loads(delegation["allowed_action_types_json"])
            if action["action_type"] not in allowed_actions:
                raise DelegatedAuthorizationError("action type outside standing delegation")

            evaluation = conn.execute(
                "SELECT * FROM standing_delegation_evaluations WHERE evaluation_id=?",
                (evaluation_id,),
            ).fetchone()
            if not evaluation:
                raise DelegatedAuthorizationError("standing evaluation missing")
            if evaluation["delegation_id"] != delegation_id:
                raise DelegatedAuthorizationError("standing evaluation belongs to different delegation")
            if evaluation["action_id"] != action_id:
                raise DelegatedAuthorizationError("standing evaluation belongs to different action")
            if evaluation["action_type"] != action["action_type"] or evaluation["action_target"] != action["target"]:
                raise DelegatedAuthorizationError("standing evaluation action binding mismatch")
            if evaluation["result"] != "current" or int(evaluation["action_in_scope"]) != 1:
                raise DelegatedAuthorizationError("standing evaluation does not support current action")

            latest = conn.execute(
                """SELECT evaluation_id FROM standing_delegation_evaluations
                   WHERE delegation_id=? AND action_id=?
                   ORDER BY evaluated_at DESC,evaluation_id DESC LIMIT 1""",
                (delegation_id, action_id),
            ).fetchone()
            if not latest or latest["evaluation_id"] != evaluation_id:
                raise DelegatedAuthorizationError("standing evaluation has been superseded by newer evaluation")
            evaluated_at = _parse_time(evaluation["evaluated_at"])
            age = (now - evaluated_at).total_seconds()
            if age < 0 or age > max_evaluation_age_seconds:
                raise DelegatedAuthorizationError("standing evaluation is stale")

            supporting_envelopes = json.loads(evaluation["supporting_envelopes_json"])
            if not supporting_envelopes:
                raise DelegatedAuthorizationError("standing evaluation has no current supporting envelopes")
            claim_ids, evidence_ids = _claim_and_evidence_ids(conn, supporting_envelopes)

            warrant = _build_warrant(
                action_row=action,
                delegation_row=delegation,
                evaluation_row=evaluation,
                claim_ids=claim_ids,
                evidence_ids=evidence_ids,
                now=now,
                ttl_seconds=ttl_seconds,
            )

            conn.execute(
                """INSERT INTO temporal_warrants
                (warrant_id,domain,action_class,subject,target,claim_ids_json,evidence_ids_json,
                 issuer,policy_basis,issued_at,valid_from,valid_to,status,scope_json,
                 completion_condition,provenance_json,created_at,updated_at,
                 superseded_by,revoked_reason,completed_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    warrant.warrant_id,warrant.domain,warrant.action_class,warrant.subject,warrant.target,
                    _json(warrant.claim_ids),_json(warrant.evidence_ids),warrant.issuer,warrant.policy_basis,
                    warrant.issued_at,warrant.valid_from,warrant.valid_to,
                    warrant.status.value if hasattr(warrant.status,"value") else warrant.status,
                    _json(warrant.scope),warrant.completion_condition,_json(warrant.provenance),
                    warrant.created_at,warrant.updated_at,warrant.superseded_by,warrant.revoked_reason,
                    warrant.completed_at,
                ),
            )
            conn.execute(
                """UPDATE action_requests
                   SET approval_required=0,approval_id=NULL,authorization_mode='standing_delegation',
                       standing_delegation_id=?,standing_evaluation_id=?,warrant_id=?,warrant_bound_at=?,
                       status='ready_for_action',updated_at=?
                   WHERE id=? AND status='waiting_approval' AND warrant_id IS NULL""",
                (delegation_id,evaluation_id,warrant.warrant_id,_iso(now),_iso(now),action_id),
            )
            binding_payload = {
                "action_id": action_id,
                "task_id": action["task_id"],
                "action_type": action["action_type"],
                "target": action["target"],
                "authority_revision": action["authority_revision"],
                "artifact_binding": _artifact_binding(action),
                "delegation_id": delegation_id,
                "evaluation_id": evaluation_id,
                "facts_sha256": evaluation["facts_sha256"],
            }
            issuance_id = f"delegated-{uuid4().hex[:20]}"
            conn.execute(
                """INSERT INTO delegated_warrant_issuances
                (issuance_id,action_id,warrant_id,delegation_id,evaluation_id,issued_at,
                 request_binding_sha256,supporting_envelopes_json,claim_ids_json,evidence_ids_json)
                VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    issuance_id,action_id,warrant.warrant_id,delegation_id,evaluation_id,_iso(now),
                    hashlib.sha256(_json(binding_payload).encode("utf-8")).hexdigest(),
                    _json(supporting_envelopes),_json(claim_ids),_json(evidence_ids),
                ),
            )
            conn.commit()
            return warrant
        except Exception:
            conn.rollback()
            raise


def validate_delegated_warrant_current(*, db, action_row: dict[str, Any], warrant: Warrant, now_iso: str) -> Warrant:
    """Revalidate standing lineage immediately before external dispatch."""
    if action_row.get("authorization_mode") != "standing_delegation":
        return warrant
    now = _parse_time(now_iso)
    delegation_id = action_row.get("standing_delegation_id")
    evaluation_id = action_row.get("standing_evaluation_id")
    if not delegation_id or not evaluation_id:
        raise DelegatedAuthorizationError("delegated action missing standing lineage")
    if warrant.provenance.get("source") != "standing_delegation":
        raise DelegatedAuthorizationError("delegated action warrant provenance mismatch")
    if warrant.provenance.get("delegation_id") != delegation_id or warrant.provenance.get("evaluation_id") != evaluation_id:
        raise DelegatedAuthorizationError("delegated warrant lineage mismatch")

    conn = db._connection()
    delegation = conn.execute(
        "SELECT * FROM standing_delegations WHERE delegation_id=?", (delegation_id,)
    ).fetchone()
    if not delegation or delegation["status"] != "active":
        raise DelegatedAuthorizationError("standing delegation is no longer active")
    if now < _parse_time(delegation["valid_from"]) or now >= _parse_time(delegation["review_by"]):
        raise DelegatedAuthorizationError("standing delegation no longer has current review standing")

    evaluation = conn.execute(
        "SELECT * FROM standing_delegation_evaluations WHERE evaluation_id=?", (evaluation_id,)
    ).fetchone()
    if not evaluation or evaluation["result"] != "current" or int(evaluation["action_in_scope"]) != 1:
        raise DelegatedAuthorizationError("standing evaluation no longer supports dispatch")
    if evaluation["action_id"] != action_row["id"] or evaluation["action_type"] != action_row["action_type"] or evaluation["action_target"] != action_row["target"]:
        raise DelegatedAuthorizationError("standing evaluation no longer matches action")
    latest = conn.execute(
        """SELECT evaluation_id FROM standing_delegation_evaluations
           WHERE delegation_id=? AND action_id=?
           ORDER BY evaluated_at DESC,evaluation_id DESC LIMIT 1""",
        (delegation_id, action_row["id"]),
    ).fetchone()
    if not latest or latest["evaluation_id"] != evaluation_id:
        raise DelegatedAuthorizationError("a newer standing evaluation supersedes this warrant lineage")

    supporting = json.loads(evaluation["supporting_envelopes_json"])
    for envelope_id in supporting:
        row = conn.execute(
            "SELECT status FROM temporal_claim_envelopes WHERE envelope_id=?", (envelope_id,)
        ).fetchone()
        if not row or row["status"] != "active":
            raise DelegatedAuthorizationError(f"supporting envelope became former: {envelope_id}")
    if warrant.scope.get("standing_facts_sha256") != evaluation["facts_sha256"]:
        raise DelegatedAuthorizationError("standing facts digest mismatch")
    return warrant
