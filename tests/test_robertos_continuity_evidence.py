from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

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


class RobertOSContinuityEvidenceTests(unittest.TestCase):
    def _db(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        return CompanyDB(Path(td.name) / "state" / "company.sqlite")

    def test_accepted_continuity_receipt_is_immutable_non_authorizing_evidence(self):
        db = self._db()
        receipt = _receipt()

        result = record_robertos_continuity_receipt(db, receipt)
        self.assertTrue(result["recorded"])
        self.assertEqual(result["authority_effect"], "none")

        event = db.get_temporal_evidence(result["evidence_id"])
        self.assertIsNotNone(event)
        self.assertEqual(event.kind.value, "system_event")
        self.assertEqual(event.subject, "robertos:project:atlas")
        self.assertEqual(event.content, receipt)
        self.assertEqual(event.related_warrant_ids, [])
        self.assertIn("non_authorizing", event.tags)
        self.assertEqual(db.list_temporal_warrants(), [])

    def test_exact_receipt_retry_is_idempotent(self):
        db = self._db()
        receipt = _receipt()

        first = record_robertos_continuity_receipt(db, receipt)
        second = record_robertos_continuity_receipt(db, receipt)

        self.assertEqual(first["evidence_id"], second["evidence_id"])
        self.assertEqual(first["sha256"], second["sha256"])
        self.assertFalse(second["recorded"])
        self.assertTrue(second["idempotent_replay"])
        self.assertEqual(len(db.list_temporal_evidence(subject="robertos:project:atlas")), 1)

    def test_tampered_receipt_fails_closed(self):
        db = self._db()
        receipt = _receipt()
        receipt["authority_context"] = {"role": "tampered"}

        with self.assertRaisesRegex(ValueError, "receipt hash mismatch"):
            record_robertos_continuity_receipt(db, receipt)
        self.assertEqual(db.list_temporal_evidence(), [])

    def test_rejected_stale_predecessor_receipt_records_history_without_authority(self):
        db = self._db()
        receipt = _receipt(disposition="rejected")

        result = record_robertos_continuity_receipt(db, receipt)
        event = db.get_temporal_evidence(result["evidence_id"])

        self.assertIsNotNone(event)
        self.assertEqual(event.content["disposition"], "rejected")
        self.assertIsNone(event.content["checkpoint_id"])
        self.assertEqual(event.provenance["authority_effect"], "none")
        self.assertEqual(db.list_temporal_warrants(), [])

    def test_invalid_accepted_head_binding_is_rejected(self):
        receipt = _receipt(current="c" * 64)
        payload = dict(receipt)
        payload.pop("receipt_hash")
        receipt["receipt_hash"] = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()

        with self.assertRaisesRegex(ValueError, "advance current_head_hash"):
            validate_robertos_continuity_receipt(receipt)


if __name__ == "__main__":
    unittest.main()
