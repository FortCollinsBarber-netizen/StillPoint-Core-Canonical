"""RobertOS continuity receipts as immutable, non-authorizing StillPoint evidence.

This bridge deliberately records state-transition evidence without minting,
renewing, extending, or otherwise implying temporal authority.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .evidence import EvidenceEvent, EvidenceKind


ROBERTOS_CONTINUITY_SCHEMA = "robertos.continuity.v1"


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _require_hash(value: Any, *, label: str) -> str:
    value = str(value or "").strip().lower()
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError(f"{label} must be a SHA-256 hex digest")
    return value


def validate_robertos_continuity_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(receipt, dict):
        raise TypeError("continuity receipt must be an object")

    normalized = dict(receipt)
    if normalized.get("schema") != ROBERTOS_CONTINUITY_SCHEMA:
        raise ValueError("unsupported RobertOS continuity receipt schema")

    activation_id = str(normalized.get("activation_id") or "").strip()
    scope = str(normalized.get("scope") or "").strip()
    disposition = str(normalized.get("disposition") or "").strip()
    reason = str(normalized.get("reason") or "").strip()
    authorized_by = str(normalized.get("authorized_by") or "").strip()
    created_at = str(normalized.get("created_at") or "").strip()

    if not activation_id.startswith("act_"):
        raise ValueError("activation_id must use the RobertOS act_ namespace")
    if not scope:
        raise ValueError("scope is required")
    if disposition not in {"accepted", "rejected"}:
        raise ValueError("disposition must be accepted or rejected")
    if not reason:
        raise ValueError("reason is required")
    if not authorized_by:
        raise ValueError("authorized_by is required")
    if not created_at:
        raise ValueError("created_at is required")

    predecessor_hash = _require_hash(
        normalized.get("predecessor_hash"), label="predecessor_hash"
    )
    candidate_hash = _require_hash(
        normalized.get("candidate_hash"), label="candidate_hash"
    )
    current_head_hash = _require_hash(
        normalized.get("current_head_hash"), label="current_head_hash"
    )

    checkpoint_id = normalized.get("checkpoint_id")
    if disposition == "accepted":
        if reason != "compare_and_activate":
            raise ValueError("accepted receipt must use compare_and_activate reason")
        if checkpoint_id is None or int(checkpoint_id) <= 0:
            raise ValueError("accepted receipt requires checkpoint_id")
        if current_head_hash != candidate_hash:
            raise ValueError("accepted receipt must advance current_head_hash to candidate_hash")
    else:
        if reason != "stale_predecessor":
            raise ValueError("rejected receipt must use stale_predecessor reason")
        if checkpoint_id is not None:
            raise ValueError("rejected receipt must not allocate checkpoint_id")
        if current_head_hash == predecessor_hash:
            raise ValueError("stale-predecessor rejection must identify a different current head")

    supplied = _require_hash(normalized.get("receipt_hash"), label="receipt_hash")
    payload = dict(normalized)
    payload.pop("receipt_hash", None)
    calculated = _sha(payload)
    if supplied != calculated:
        raise ValueError("continuity receipt hash mismatch")

    normalized.update(
        {
            "activation_id": activation_id,
            "scope": scope,
            "predecessor_hash": predecessor_hash,
            "candidate_hash": candidate_hash,
            "current_head_hash": current_head_hash,
            "disposition": disposition,
            "reason": reason,
            "authorized_by": authorized_by,
            "created_at": created_at,
            "checkpoint_id": int(checkpoint_id) if checkpoint_id is not None else None,
            "authority_context": dict(normalized.get("authority_context") or {}),
            "receipt_hash": supplied,
        }
    )
    return normalized


def continuity_evidence_id(activation_id: str) -> str:
    return f"robertos-continuity:{activation_id}"


def record_robertos_continuity_receipt(db, receipt: dict[str, Any]) -> dict[str, Any]:
    """Persist one RobertOS continuity receipt as immutable StillPoint evidence.

    Replaying an identical receipt is idempotent. Reusing an activation ID with
    different content fails closed. The resulting evidence has no related
    warrants and confers no action authority.
    """

    normalized = validate_robertos_continuity_receipt(receipt)
    evidence_id = continuity_evidence_id(normalized["activation_id"])
    event = EvidenceEvent(
        evidence_id=evidence_id,
        kind=EvidenceKind.SYSTEM_EVENT,
        subject=f"robertos:{normalized['scope']}",
        content=normalized,
        source="RobertOS",
        observed_at=normalized["created_at"],
        recorded_at=normalized["created_at"],
        related_claim_ids=[],
        related_warrant_ids=[],
        tags=[
            "robertos",
            "continuity",
            "activation_receipt",
            normalized["disposition"],
            "non_authorizing",
        ],
        provenance={
            "schema": ROBERTOS_CONTINUITY_SCHEMA,
            "activation_id": normalized["activation_id"],
            "receipt_hash": normalized["receipt_hash"],
            "authority_effect": "none",
            "warrant_minted": False,
        },
    )

    existing = db.get_temporal_evidence(evidence_id)
    if existing is not None:
        if existing.sha256 != event.sha256 or existing.to_dict() != event.to_dict():
            raise RuntimeError("continuity activation_id already exists with different evidence")
        return {
            "evidence_id": existing.evidence_id,
            "sha256": existing.sha256,
            "subject": existing.subject,
            "recorded": False,
            "idempotent_replay": True,
            "authority_effect": "none",
        }

    db.add_temporal_evidence(event)
    stored = db.get_temporal_evidence(evidence_id)
    if stored is None:
        raise RuntimeError("continuity evidence did not persist")
    return {
        "evidence_id": stored.evidence_id,
        "sha256": stored.sha256,
        "subject": stored.subject,
        "recorded": True,
        "idempotent_replay": False,
        "authority_effect": "none",
    }
