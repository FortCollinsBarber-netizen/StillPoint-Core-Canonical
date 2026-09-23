from __future__ import annotations

import hashlib
import json

import pytest

from stillpoint.db import CompanyDB
from stillpoint.temporal.continuity_ingress import (
    record_robertos_continuity_receipt,
    validate_robertos_continuity_receipt,
)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _receipt(*, disposition="accepted", candidate="b" * 64, current=None):
    payload = {
        "schema": "robertos.continuity.v1",
        "activation_id": "act_1234567890abcdef12345678",
        "scope": "project:atlas",
        "predecessor_hash": "a" * 64,
        "candidate_hash": candidate,
        "disposition": disposition,
        "reason": "compare_and_activate" if disposition == "accepted" else "stale_predecessor",
        "checkpoint_id": 7 if disposition == "accepted" else None,
        "current_head_hash": current or (candidate if disposition == "accepted" else "c" * 64),
        "authorized_by": "Robert Emmanuel LaDay",
        "authority_context": {"role": "CEO"},
        "created_at": "2026-09-23T12:00:00+00:00",
    }
    payload["receipt_hash"] = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    return payload


def test_accepted_continuity_receipt_is_immutable_non_authorizing_evidence(tmp_path):
    db = CompanyDB(tmp_path / "state" / "company.sqlite")
    receipt = _receipt()

    result = record_robertos_continuity_receipt(db, receipt)
    assert result["recorded"] is True
    assert result["authority_effect"] == "none"

    event = db.get_temporal_evidence(result["evidence_id"])
    assert event is not None
    assert event.kind.value == "system_event"
    assert event.subject == "robertos:project:atlas"
    assert event.content == receipt
    assert event.related_warrant_ids == []
    assert "non_authorizing" in event.tags
    assert db.list_temporal_warrants() == []


def test_exact_receipt_retry_is_idempotent(tmp_path):
    db = CompanyDB(tmp_path / "state" / "company.sqlite")
    receipt = _receipt()

    first = record_robertos_continuity_receipt(db, receipt)
    second = record_robertos_continuity_receipt(db, receipt)

    assert first["evidence_id"] == second["evidence_id"]
    assert first["sha256"] == second["sha256"]
    assert second["recorded"] is False
    assert second["idempotent_replay"] is True
    assert len(db.list_temporal_evidence(subject="robertos:project:atlas")) == 1


def test_tampered_receipt_fails_closed(tmp_path):
    db = CompanyDB(tmp_path / "state" / "company.sqlite")
    receipt = _receipt()
    receipt["candidate_hash"] = "d" * 64

    with pytest.raises(ValueError, match="receipt hash mismatch"):
        record_robertos_continuity_receipt(db, receipt)
    assert db.list_temporal_evidence() == []


def test_rejected_stale_predecessor_receipt_records_history_without_authority(tmp_path):
    db = CompanyDB(tmp_path / "state" / "company.sqlite")
    receipt = _receipt(disposition="rejected")

    result = record_robertos_continuity_receipt(db, receipt)
    event = db.get_temporal_evidence(result["evidence_id"])

    assert event is not None
    assert event.content["disposition"] == "rejected"
    assert event.content["checkpoint_id"] is None
    assert event.provenance["authority_effect"] == "none"
    assert db.list_temporal_warrants() == []


def test_invalid_accepted_head_binding_is_rejected():
    receipt = _receipt(current="c" * 64)
    payload = dict(receipt)
    payload.pop("receipt_hash")
    receipt["receipt_hash"] = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()

    with pytest.raises(ValueError, match="advance current_head_hash"):
        validate_robertos_continuity_receipt(receipt)
