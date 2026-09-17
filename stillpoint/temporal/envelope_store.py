"""Persistence helpers for Claim Envelopes and Continuing Evidence context.

The store persists epistemic/operational context only. It contains no method
that issues, renews, extends, or substitutes for a temporal warrant.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from .envelope import (
    ClaimEnvelope,
    ClaimUseEvent,
    ContinuationCondition,
    EpistemicReach,
    EnvelopeStatus,
    EvidenceContext,
    MemoryPolicy,
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _loads(value: str | None, default):
    if not value:
        return default
    return json.loads(value)


class ClaimEnvelopeStore:
    def __init__(self, db):
        self.db = db

    def persist(self, envelope: ClaimEnvelope) -> str:
        conn = self.db._connection()
        conn.execute(
            """INSERT INTO temporal_claim_envelopes
            (envelope_id,claim_id,domain,purpose,epistemic_reach_json,permitted_uses_json,
             prohibited_uses_json,continuation_conditions_json,correction_routes_json,
             release_conditions_json,reentry_requirements_json,memory_policy_json,
             memory_may_reauthorize,operational,status,supersedes_envelope_id,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                envelope.envelope_id,
                envelope.claim_id,
                envelope.domain,
                envelope.purpose,
                _json(envelope.epistemic_reach.to_dict()),
                _json(envelope.permitted_uses),
                _json(envelope.prohibited_uses),
                _json([c.to_dict() for c in envelope.continuation_conditions]),
                _json(envelope.correction_routes),
                _json(envelope.release_conditions),
                _json(envelope.reentry_requirements),
                _json(envelope.memory_policy.to_dict()),
                0,
                1 if envelope.operational else 0,
                envelope.status.value,
                envelope.supersedes_envelope_id,
                envelope.created_at,
                envelope.created_at,
            ),
        )
        conn.commit()
        return envelope.envelope_id

    def get(self, envelope_id: str) -> ClaimEnvelope | None:
        row = self.db._connection().execute(
            "SELECT * FROM temporal_claim_envelopes WHERE envelope_id=?", (envelope_id,)
        ).fetchone()
        return self._from_row(row) if row else None

    def get_active_for_claim(self, claim_id: str) -> ClaimEnvelope | None:
        row = self.db._connection().execute(
            "SELECT * FROM temporal_claim_envelopes WHERE claim_id=? AND status='active'",
            (claim_id,),
        ).fetchone()
        return self._from_row(row) if row else None

    def supersede(self, prior_envelope_id: str, new_envelope: ClaimEnvelope) -> str:
        if new_envelope.supersedes_envelope_id not in {None, prior_envelope_id}:
            raise ValueError("new envelope supersedes a different envelope")
        conn = self.db._connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            prior = conn.execute(
                "SELECT * FROM temporal_claim_envelopes WHERE envelope_id=?", (prior_envelope_id,)
            ).fetchone()
            if not prior:
                raise KeyError(prior_envelope_id)
            if prior["status"] != "active":
                raise RuntimeError("only an active envelope can be superseded")
            if prior["claim_id"] != new_envelope.claim_id:
                raise ValueError("superseding envelope must bind the same claim")
            now = _utcnow()
            # End the prior envelope's operational standing first so the partial
            # unique index permits the replacement. The forward link is written
            # only after the replacement row exists, preserving FK integrity.
            conn.execute(
                """UPDATE temporal_claim_envelopes
                   SET status='superseded',updated_at=?
                   WHERE envelope_id=? AND status='active'""",
                (now, prior_envelope_id),
            )
            prepared = replace(new_envelope, supersedes_envelope_id=prior_envelope_id)
            conn.execute(
                """INSERT INTO temporal_claim_envelopes
                (envelope_id,claim_id,domain,purpose,epistemic_reach_json,permitted_uses_json,
                 prohibited_uses_json,continuation_conditions_json,correction_routes_json,
                 release_conditions_json,reentry_requirements_json,memory_policy_json,
                 memory_may_reauthorize,operational,status,supersedes_envelope_id,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    prepared.envelope_id,
                    prepared.claim_id,
                    prepared.domain,
                    prepared.purpose,
                    _json(prepared.epistemic_reach.to_dict()),
                    _json(prepared.permitted_uses),
                    _json(prepared.prohibited_uses),
                    _json([c.to_dict() for c in prepared.continuation_conditions]),
                    _json(prepared.correction_routes),
                    _json(prepared.release_conditions),
                    _json(prepared.reentry_requirements),
                    _json(prepared.memory_policy.to_dict()),
                    0,
                    1 if prepared.operational else 0,
                    prepared.status.value,
                    prepared.supersedes_envelope_id,
                    prepared.created_at,
                    prepared.created_at,
                ),
            )
            conn.execute(
                """UPDATE temporal_claim_envelopes
                   SET superseded_by_envelope_id=?,updated_at=?
                   WHERE envelope_id=? AND status='superseded'""",
                (prepared.envelope_id, now, prior_envelope_id),
            )
            conn.commit()
            return prepared.envelope_id
        except Exception:
            conn.rollback()
            raise

    def record_use(self, event: ClaimUseEvent) -> str:
        conn = self.db._connection()
        conn.execute(
            """INSERT INTO temporal_claim_use_events
            (use_id,claim_id,envelope_id,use_kind,actor,purpose,occurred_at,warrant_id,action_id,
             intervention_effects_json,metadata_json)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (
                event.use_id,
                event.claim_id,
                event.envelope_id,
                event.use_kind.value,
                event.actor,
                event.purpose,
                event.occurred_at,
                event.warrant_id,
                event.action_id,
                _json(event.intervention_effects),
                _json(event.metadata),
            ),
        )
        conn.commit()
        return event.use_id

    def list_uses(self, claim_id: str) -> list[dict[str, Any]]:
        rows = self.db._connection().execute(
            "SELECT * FROM temporal_claim_use_events WHERE claim_id=? ORDER BY occurred_at,use_id",
            (claim_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def record_evidence_context(self, context: EvidenceContext) -> str:
        conn = self.db._connection()
        conn.execute(
            """INSERT INTO temporal_evidence_contexts
            (evidence_id,environment,prior_use_ids_json,system_influence_json,recorded_at)
            VALUES(?,?,?,?,?)""",
            (
                context.evidence_id,
                context.environment.value,
                _json(context.prior_use_ids),
                _json(context.system_influence),
                context.recorded_at,
            ),
        )
        conn.commit()
        return context.evidence_id

    @staticmethod
    def _from_row(row) -> ClaimEnvelope:
        reach = EpistemicReach(**_loads(row["epistemic_reach_json"], {}))
        conditions = [ContinuationCondition(**item) for item in _loads(row["continuation_conditions_json"], [])]
        memory = MemoryPolicy(**_loads(row["memory_policy_json"], {}))
        return ClaimEnvelope(
            envelope_id=row["envelope_id"],
            claim_id=row["claim_id"],
            domain=row["domain"],
            purpose=row["purpose"],
            epistemic_reach=reach,
            permitted_uses=_loads(row["permitted_uses_json"], []),
            prohibited_uses=_loads(row["prohibited_uses_json"], []),
            continuation_conditions=conditions,
            correction_routes=_loads(row["correction_routes_json"], []),
            release_conditions=_loads(row["release_conditions_json"], []),
            reentry_requirements=_loads(row["reentry_requirements_json"], []),
            memory_policy=memory,
            operational=bool(row["operational"]),
            status=EnvelopeStatus(row["status"]),
            supersedes_envelope_id=row["supersedes_envelope_id"],
            created_at=row["created_at"],
        )
