from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from stillpoint.temporal.claims import Claim, ClaimDomain, ClaimStatus
from stillpoint.temporal.evidence import EvidenceEvent, EvidenceKind
from stillpoint.temporal.firewall import DomainContainment, TemporalAuthorityError
from stillpoint.temporal.reentry import ReleaseRecord, release_warrant
from stillpoint.temporal.warrants import Warrant, WarrantStatus


def now():
    return datetime.now(timezone.utc)


def valid_warrant(**overrides):
    t = now()
    data = dict(
        warrant_id="w1",
        domain="publishing",
        action_class="publish",
        subject="task:abc",
        target="public",
        issuer="CEO:Robert Emmanuel LaDay",
        policy_basis="explicit_ceo_authorization",
        valid_from=(t - timedelta(minutes=1)).isoformat(),
        valid_to=(t + timedelta(minutes=10)).isoformat(),
        scope={"targets": ["public"]},
    )
    data.update(overrides)
    return Warrant(**data)


class TemporalHardeningTests(unittest.TestCase):
    def test_unknown_warrant_status_never_becomes_active(self):
        w = Warrant.from_dict({
            **valid_warrant().to_dict(),
            "status": "revokedd",
        })
        self.assertEqual(w.status, WarrantStatus.REVIEW_REQUIRED)
        self.assertFalse(w.is_active())

    def test_malformed_warrant_time_fails_closed(self):
        w = valid_warrant(valid_to="not-a-time")
        self.assertFalse(w.is_active())

    def test_active_warrant_requires_finite_end(self):
        w = valid_warrant(valid_to=None)
        self.assertFalse(w.is_active())

    def test_wrong_subject_is_denied(self):
        w = valid_warrant()
        self.assertFalse(w.permits("publish", "publishing", "task:other", target="public"))

    def test_wrong_target_is_denied(self):
        w = valid_warrant()
        self.assertFalse(w.permits("publish", "publishing", "task:abc", target="vendor"))

    def test_unknown_claim_status_is_review_required(self):
        c = Claim.from_dict({
            "claim_id": "c1",
            "subject": "s",
            "predicate": "p",
            "value": 1,
            "domain": "general",
            "source": "test",
            "status": "totally_new_state",
        })
        self.assertEqual(c.status, ClaimStatus.REVIEW_REQUIRED)
        self.assertFalse(c.is_current())

    def test_malformed_claim_boundary_is_not_current(self):
        c = Claim(
            claim_id="c1",
            subject="s",
            predicate="p",
            value=1,
            domain=ClaimDomain.GENERAL,
            source="test",
            effective_to="garbage",
        )
        self.assertFalse(c.is_current())

    def test_sensitive_cross_domain_requires_explicit_promotion(self):
        gate = DomainContainment()
        with self.assertRaises(TemporalAuthorityError):
            gate.assert_domain_compatible("medical", "general", "employment")

        gate.assert_domain_compatible(
            "medical",
            "employment",
            "employment",
            explicit_cross_domain_claim_domains={"medical"},
        )

    def test_evidence_hash_is_bound_to_content(self):
        e = EvidenceEvent(
            evidence_id="e1",
            kind=EvidenceKind.OBSERVATION,
            subject="s",
            content={"x": 1},
            source="test",
        )
        self.assertTrue(e.sha256)
        with self.assertRaises(ValueError):
            EvidenceEvent(
                evidence_id="e2",
                kind=EvidenceKind.OBSERVATION,
                subject="s",
                content={"x": 1},
                source="test",
                sha256="0" * 64,
            )

    def test_release_is_bound_to_exact_warrant_and_subject(self):
        w = valid_warrant()
        wrong = ReleaseRecord(
            release_id="r1",
            subject="task:abc",
            prior_warrant_id="different",
        )
        with self.assertRaises(ValueError):
            release_warrant(w, wrong)

        good = ReleaseRecord(
            release_id="r2",
            subject="task:abc",
            prior_warrant_id="w1",
        )
        release_warrant(w, good)
        self.assertEqual(w.status, WarrantStatus.COMPLETED)

    def test_release_string_false_is_rejected_not_truthy(self):
        with self.assertRaises(ValueError):
            ReleaseRecord.from_dict({
                "release_id": "r",
                "subject": "s",
                "retains_historical_record": "false",
            })


if __name__ == "__main__":
    unittest.main()
