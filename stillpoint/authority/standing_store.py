"""Persistence for standing delegations and append-only standing evaluations."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from stillpoint.temporal.envelope import ContinuationCondition
from .standing import DelegationAssessment, DelegationStatus, StandingDelegation


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _loads(value: str | None, default):
    if not value:
        return default
    return json.loads(value)


class StandingDelegationStore:
    def __init__(self, db):
        self.db = db

    def persist(self, delegation: StandingDelegation) -> str:
        conn = self.db._connection()
        conn.execute(
            """INSERT INTO standing_delegations
            (delegation_id,delegate_role,issuer,policy_basis,purpose,claim_envelope_ids_json,
             allowed_action_types_json,continuation_conditions_json,execution_conditions_json,
             exclusions_json,release_conditions_json,valid_from,review_by,status,
             supersedes_delegation_id,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                delegation.delegation_id,
                delegation.delegate_role,
                delegation.issuer,
                delegation.policy_basis,
                delegation.purpose,
                _json(delegation.claim_envelope_ids),
                _json(delegation.allowed_action_types),
                _json([c.to_dict() for c in delegation.continuation_conditions]),
                _json([c.to_dict() for c in delegation.execution_conditions]),
                _json(delegation.exclusions),
                _json(delegation.release_conditions),
                delegation.valid_from,
                delegation.review_by,
                delegation.status.value,
                delegation.supersedes_delegation_id,
                delegation.created_at,
                delegation.created_at,
            ),
        )
        conn.commit()
        return delegation.delegation_id

    def get(self, delegation_id: str) -> StandingDelegation | None:
        row = self.db._connection().execute(
            "SELECT * FROM standing_delegations WHERE delegation_id=?", (delegation_id,)
        ).fetchone()
        return self._from_row(row) if row else None

    def record_assessment(
        self,
        *,
        delegation_id: str,
        assessment: DelegationAssessment,
        evaluated_at: str,
        continuation_facts: dict[str, Any],
        execution_facts: dict[str, Any],
        action_id: str,
        action_type: str,
        action_target: str,
    ) -> str:
        evaluation_id = f"eval-{uuid4().hex[:20]}"
        facts_payload = {
            "continuation": continuation_facts,
            "execution": execution_facts,
            "action_id": action_id,
            "action_type": action_type,
            "action_target": action_target,
        }
        digest = hashlib.sha256(_json(facts_payload).encode("utf-8")).hexdigest()
        conn = self.db._connection()
        conn.execute(
            """INSERT INTO standing_delegation_evaluations
            (evaluation_id,delegation_id,evaluated_at,action_id,action_type,action_target,
             facts_sha256,result,action_in_scope,failed_conditions_json,supporting_envelopes_json,note)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                evaluation_id,
                delegation_id,
                evaluated_at,
                action_id,
                action_type,
                action_target,
                digest,
                assessment.standing.value,
                1 if assessment.action_in_scope else 0,
                _json(assessment.failed_conditions),
                _json(assessment.supporting_envelopes),
                assessment.note,
            ),
        )
        conn.commit()
        return evaluation_id

    @staticmethod
    def _from_row(row) -> StandingDelegation:
        return StandingDelegation(
            delegation_id=row["delegation_id"],
            delegate_role=row["delegate_role"],
            issuer=row["issuer"],
            policy_basis=row["policy_basis"],
            purpose=row["purpose"],
            claim_envelope_ids=_loads(row["claim_envelope_ids_json"], []),
            allowed_action_types=_loads(row["allowed_action_types_json"], []),
            continuation_conditions=[
                ContinuationCondition(**item)
                for item in _loads(row["continuation_conditions_json"], [])
            ],
            execution_conditions=[
                ContinuationCondition(**item)
                for item in _loads(row["execution_conditions_json"], [])
            ],
            exclusions=_loads(row["exclusions_json"], []),
            release_conditions=_loads(row["release_conditions_json"], []),
            valid_from=row["valid_from"],
            review_by=row["review_by"],
            status=DelegationStatus(row["status"]),
            supersedes_delegation_id=row["supersedes_delegation_id"],
            created_at=row["created_at"],
        )
