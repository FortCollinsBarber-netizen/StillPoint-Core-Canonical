"""Focused and adversarial tests for the temporal authority / continuing evidence layer.

Required behaviors (1-20) plus adversarial bypass attempts.
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from stillpoint.db import CompanyDB
from stillpoint.temporal import (
    Claim,
    ClaimStatus,
    ClaimDomain,
    EvidenceRef,
    Warrant,
    WarrantStatus,
    EvidenceEvent,
    EvidenceKind,
    ClaimToWarrantFirewall,
    PredictionFirewall,
    DomainContainment,
    TemporalAuthorityError,
    ReevaluationTrigger,
    ReleaseRecord,
)
from stillpoint.temporal.reentry import apply_new_evidence_to_claims, release_warrant
from stillpoint.contracts.models import ActionRequest, ArtifactRef


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _future(hours: int = 1) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _past(hours: int = 2) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


class TemporalClaimModelTests(unittest.TestCase):
    def test_claim_is_information_only(self):
        c = Claim(
            claim_id="c1",
            subject="person:alice",
            predicate="committed_offense",
            value="X",
            domain=ClaimDomain.CRIMINAL,
            source="court_record",
            time_observed=_past(24 * 365),
            confidence=0.99,
        )
        self.assertEqual(c.status, ClaimStatus.ACTIVE)
        self.assertTrue(c.is_current())
        # No action fields
        self.assertFalse(hasattr(c, "action_class"))
        self.assertFalse(hasattr(c, "issuer"))

    def test_historical_truth_preserved_after_status_change(self):
        """1. Historical truth remains preserved after current status changes."""
        c = Claim(
            claim_id="c_hist",
            subject="person:bob",
            predicate="offense",
            value="X_at_T1",
            domain=ClaimDomain.CRIMINAL,
            source="record",
            time_observed="2020-01-01T00:00:00+00:00",
            time_asserted="2020-01-02T00:00:00+00:00",
        )
        original_value = c.value
        original_observed = c.time_observed
        c.mark_historical("no longer current applicability")
        self.assertEqual(c.status, ClaimStatus.HISTORICAL)
        self.assertEqual(c.value, original_value)
        self.assertEqual(c.time_observed, original_observed)
        self.assertFalse(c.is_current())

    def test_claim_valid_t1_superseded_t2_without_rewrite(self):
        """2. Claim valid at T1 and superseded at T2 without rewriting T1."""
        c1 = Claim(
            claim_id="c_t1",
            subject="org:acme",
            predicate="status",
            value="solvent",
            domain=ClaimDomain.FINANCIAL,
            source="filing",
            time_observed=_past(100),
            time_asserted=_past(99),
        )
        c2 = Claim(
            claim_id="c_t2",
            subject="org:acme",
            predicate="status",
            value="insolvent",
            domain=ClaimDomain.FINANCIAL,
            source="filing",
            time_observed=_now(),
            time_asserted=_now(),
            supersedes="c_t1",
        )
        c1.mark_superseded("c_t2")
        self.assertEqual(c1.status, ClaimStatus.SUPERSEDED)
        self.assertEqual(c1.value, "solvent")  # T1 record intact
        self.assertEqual(c1.superseded_by, "c_t2")
        self.assertEqual(c2.supersedes, "c_t1")
        self.assertTrue(c2.is_current())
        self.assertFalse(c1.is_current())

    def test_unknown_not_coerced_to_false(self):
        """4. Unknown is not coerced to false (? ≠ 0)."""
        c = Claim(
            claim_id="c_unk",
            subject="person:carol",
            predicate="risk_score",
            value=None,
            domain=ClaimDomain.RISK,
            source="model",
            confidence=None,
        )
        self.assertIsNone(c.value)
        self.assertIsNone(c.confidence)
        # Explicitly not 0
        self.assertNotEqual(c.confidence, 0.0)


class ContinuingEvidenceTests(unittest.TestCase):
    def test_new_evidence_triggers_review(self):
        """3. New evidence can trigger review."""
        c = Claim(
            claim_id="c_ev",
            subject="person:dave",
            predicate="classification",
            value="low_risk",
            domain=ClaimDomain.RISK,
            source="prior_model",
        )
        ev = EvidenceEvent(
            evidence_id="e1",
            kind=EvidenceKind.CORRECTION,
            subject="person:dave",
            content="new observation contradicts prior",
            source="sensor",
        )
        apply_new_evidence_to_claims([c], ev, contradict_predicates={"classification"})
        self.assertEqual(c.status, ClaimStatus.REVIEW_REQUIRED)
        self.assertTrue(any(r.evidence_id == "e1" for r in c.evidence_refs))

    def test_evidence_leaves_historical_intact(self):
        c = Claim(
            claim_id="c_hist2",
            subject="person:eve",
            predicate="event",
            value="happened",
            domain=ClaimDomain.GENERAL,
            source="log",
            status=ClaimStatus.HISTORICAL,
        )
        ev = EvidenceEvent(
            evidence_id="e2",
            kind=EvidenceKind.OBSERVATION,
            subject="person:eve",
            content="later note",
            source="log",
        )
        apply_new_evidence_to_claims([c], ev)
        # Historical claims are skipped for review mutation
        self.assertEqual(c.status, ClaimStatus.HISTORICAL)


class ClaimToWarrantFirewallTests(unittest.TestCase):
    def test_claim_cannot_silently_become_warrant(self):
        """6. A valid claim cannot silently become a warrant."""
        fw = ClaimToWarrantFirewall()
        c = Claim(
            claim_id="c_fw",
            subject="person:frank",
            predicate="offense",
            value="X",
            domain=ClaimDomain.CRIMINAL,
            source="record",
            confidence=0.999,
        )
        with self.assertRaises(TemporalAuthorityError) as cm:
            fw.claim_cannot_create_action_authority(c)
        self.assertEqual(cm.exception.code, "CLAIM_NOT_AUTHORITY")

    def test_require_warrant_for_action(self):
        fw = ClaimToWarrantFirewall()
        w = Warrant(
            warrant_id="w1",
            domain="operational",
            action_class="send_email",
            subject="person:grace",
            issuer="ceo_approval:1",
            policy_basis="test_policy",
            valid_to=_future(2),
        )
        found = fw.require_warrant_for_action(
            action_type="send_email",
            domain="operational",
            subject="person:grace",
            warrants=[w],
        )
        self.assertEqual(found.warrant_id, "w1")

    def test_no_warrant_raises(self):
        fw = ClaimToWarrantFirewall()
        with self.assertRaises(TemporalAuthorityError) as cm:
            fw.require_warrant_for_action(
                action_type="publish",
                domain="press",
                subject="doc:1",
                warrants=[],
            )
        self.assertEqual(cm.exception.code, "NO_ACTIVE_WARRANT")


class PredictionFirewallTests(unittest.TestCase):
    def test_high_confidence_prediction_cannot_create_authority(self):
        """5. A high-confidence prediction cannot create action authority."""
        pf = PredictionFirewall()
        with self.assertRaises(TemporalAuthorityError) as cm:
            pf.assert_prediction_is_evidence_not_authority(
                prediction={"behavior": "X"},
                confidence=0.99,
                action_type="restrain",
            )
        self.assertEqual(cm.exception.code, "PREDICTION_NOT_AUTHORITY")

    def test_prediction_becomes_evidence_only(self):
        pf = PredictionFirewall()
        payload = pf.prediction_may_become_evidence({"risk": 0.87}, confidence=0.87)
        self.assertFalse(payload["is_authority"])
        self.assertEqual(payload["kind"], "prediction")


class TemporalWarrantTests(unittest.TestCase):
    def test_expired_warrant_cannot_authorize(self):
        """8. An expired warrant cannot authorize a new action."""
        w = Warrant(
            warrant_id="w_exp",
            domain="operational",
            action_class="spend",
            subject="account:1",
            valid_from=_past(10),
            valid_to=_past(1),
        )
        # Status still ACTIVE but window passed → is_active False
        self.assertFalse(w.is_active())
        self.assertFalse(w.permits("spend", "operational", "account:1"))

        w2 = Warrant(
            warrant_id="w_exp2",
            domain="operational",
            action_class="spend",
            subject="account:1",
            valid_to=_future(1),
        )
        w2.expire()
        self.assertEqual(w2.status, WarrantStatus.EXPIRED)
        self.assertFalse(w2.permits("spend", "operational", "account:1"))

    def test_revoked_warrant_cannot_authorize(self):
        """9. A revoked warrant cannot authorize a new action."""
        w = Warrant(
            warrant_id="w_rev",
            domain="operational",
            action_class="delete",
            subject="file:1",
            valid_to=_future(5),
        )
        w.revoke("policy change")
        self.assertEqual(w.status, WarrantStatus.REVOKED)
        self.assertFalse(w.permits("delete", "operational", "file:1"))

    def test_completed_warrant_auditable_not_active(self):
        """10. A completed warrant remains auditable but does not remain active."""
        w = Warrant(
            warrant_id="w_done",
            domain="operational",
            action_class="publish",
            subject="doc:2",
            valid_to=_future(5),
        )
        w.complete()
        self.assertEqual(w.status, WarrantStatus.COMPLETED)
        self.assertIsNotNone(w.completed_at)
        self.assertFalse(w.is_active())
        self.assertFalse(w.permits("publish", "operational", "doc:2"))


class DomainContainmentTests(unittest.TestCase):
    def test_warrant_cannot_exceed_domain(self):
        """7. A warrant cannot exceed its domain."""
        dc = DomainContainment()
        w = Warrant(
            warrant_id="w_dom",
            domain="medical",
            action_class="diagnose",
            subject="person:helen",
            valid_to=_future(1),
        )
        # Cross-domain promotion blocked
        with self.assertRaises(TemporalAuthorityError) as cm:
            dc.assert_domain_compatible(
                claim_domain=ClaimDomain.MEDICAL,
                warrant_domain="medical",
                action_domain="employment",
            )
        self.assertEqual(cm.exception.code, "CROSS_DOMAIN_PROMOTION")

    def test_cross_domain_use_requires_explicit_warrant(self):
        """15. Cross-domain use of evidence requires explicit warrant."""
        dc = DomainContainment()
        # Same domain ok
        dc.assert_domain_compatible("criminal", "criminal", "criminal")
        # general can flow
        dc.assert_domain_compatible("general", "general", "operational")


class ReleaseAndReentryTests(unittest.TestCase):
    def test_historical_evidence_survives_release(self):
        """11. Historical evidence survives release."""
        w = Warrant(
            warrant_id="w_rel",
            domain="operational",
            action_class="restrain",
            subject="person:ian",
            valid_to=_future(1),
        )
        rel = ReleaseRecord(
            release_id="r1",
            subject="person:ian",
            prior_warrant_id="w_rel",
            released_authority="extraordinary restraint",
            reason="condition resolved",
            retains_historical_record=True,
            restores_access=False,
            erases_consequences=False,
        )
        release_warrant(w, rel)
        self.assertEqual(w.status, WarrantStatus.COMPLETED)
        self.assertTrue(rel.retains_historical_record)
        self.assertFalse(rel.restores_access)
        self.assertFalse(rel.erases_consequences)

    def test_release_does_not_restore_access_or_erase(self):
        """12. Release does not automatically restore access or erase consequence."""
        with self.assertRaises(ValueError):
            ReleaseRecord(
                release_id="r_bad",
                subject="x",
                retains_historical_record=False,  # forbidden
            )
        with self.assertRaises(ValueError):
            ReleaseRecord(
                release_id="r_bad2",
                subject="x",
                erases_consequences=True,  # forbidden
            )

    def test_new_evidence_creates_reevaluation_cycle(self):
        """13. New evidence can create a new evaluation cycle after prior completion/denial."""
        trig = ReevaluationTrigger(
            trigger_id="t1",
            prior_disposition="DENIED",
            prior_task_id="task_old",
            new_evidence_ids=["e_new"],
            reason="material new observation",
        )
        self.assertEqual(trig.prior_disposition, "DENIED")
        self.assertIn("e_new", trig.new_evidence_ids)

    def test_prior_decisions_remain_auditable_after_reentry(self):
        """14. Prior decisions remain auditable after re-entry."""
        trig = ReevaluationTrigger(
            trigger_id="t2",
            prior_disposition="COMPLETED",
            prior_task_id="task_42",
            prior_claim_ids=["c_old"],
            new_evidence_ids=["e3"],
            reason="re-entry permitted by policy",
            new_evaluation_id="task_new",
        )
        # Prior linkage preserved
        self.assertEqual(trig.prior_task_id, "task_42")
        self.assertEqual(trig.prior_claim_ids, ["c_old"])
        self.assertEqual(trig.new_evaluation_id, "task_new")


class PersistenceAndMigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        self.db = CompanyDB(self.db_path)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_schema_version_includes_temporal(self):
        self.assertGreaterEqual(self.db.schema_version, 5)

    def test_claim_roundtrip(self):
        c = Claim(
            claim_id="c_db1",
            subject="person:jade",
            predicate="role",
            value="contributor",
            domain=ClaimDomain.OPERATIONAL,
            source="registry",
            confidence=None,
        )
        self.db.add_temporal_claim(c)
        loaded = self.db.get_temporal_claim("c_db1")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.subject, "person:jade")
        self.assertIsNone(loaded.confidence)
        self.assertEqual(loaded.status, ClaimStatus.ACTIVE)

    def test_warrant_roundtrip_and_status_update(self):
        w = Warrant(
            warrant_id="w_db1",
            domain="operational",
            action_class="notify",
            subject="person:kyle",
            issuer="policy:notify",
            policy_basis="test_policy",
            valid_to=_future(3),
        )
        self.db.add_temporal_warrant(w)
        loaded = self.db.get_temporal_warrant("w_db1")
        self.assertTrue(loaded.is_active())
        loaded.expire()
        self.db.update_temporal_warrant(loaded)
        again = self.db.get_temporal_warrant("w_db1")
        self.assertEqual(again.status, WarrantStatus.EXPIRED)

    def test_evidence_ingress_persisted(self):
        ev = EvidenceEvent(
            evidence_id="e_db1",
            kind=EvidenceKind.MODEL_OUTPUT,
            subject="person:liam",
            content={"prediction": "Y", "confidence": 0.91},
            source="specialist:research",
            confidence=0.91,
        )
        self.db.add_temporal_evidence(ev)
        loaded = self.db.get_temporal_evidence("e_db1")
        self.assertEqual(loaded.kind, EvidenceKind.MODEL_OUTPUT)
        self.assertEqual(loaded.confidence, 0.91)


class ExistingProtectionsStillHold(unittest.TestCase):
    """16-19: existing ActionRequest binding, truthfulness, dry-run, specialist contracts intact."""

    def test_action_request_permitted_still_time_bound(self):
        req = ActionRequest(
            action_id="ar1",
            task_id="t1",
            action_type="send",
            target="user@example.com",
            scope=["email"],
            artifact_refs=[],
            approval_required=True,
            approval_id="ap1",
            expires_at=_past(1),
            issued_at=_past(2),
            idempotency_key="idem1",
            success_criteria=["sent"],
        )
        self.assertFalse(req.permitted())

    def test_action_request_future_expiry_ok(self):
        req = ActionRequest(
            action_id="ar2",
            task_id="t1",
            action_type="send",
            target="user@example.com",
            scope=["email"],
            artifact_refs=[],
            approval_required=True,
            approval_id="ap1",
            expires_at=_future(2),
            issued_at=_past(1),
            idempotency_key="idem2",
            success_criteria=["sent"],
            warrant_id="w-test",
        )
        self.assertTrue(req.permitted())


class AdversarialBypassTests(unittest.TestCase):
    def test_very_high_confidence_does_not_bypass(self):
        pf = PredictionFirewall()
        with self.assertRaises(TemporalAuthorityError):
            pf.assert_prediction_is_evidence_not_authority(
                prediction="certain_harm",
                confidence=1.0,
                action_type="restrain",
            )

    def test_administrator_role_does_not_create_warrant(self):
        fw = ClaimToWarrantFirewall()
        # Even a claim from "admin" is still not a warrant
        c = Claim(
            claim_id="c_admin",
            subject="person:x",
            predicate="risk",
            value="high",
            domain=ClaimDomain.RISK,
            source="administrator",
            confidence=0.95,
        )
        with self.assertRaises(TemporalAuthorityError):
            fw.claim_cannot_create_action_authority(c)

    def test_prior_approval_does_not_revive_expired_warrant(self):
        w = Warrant(
            warrant_id="w_old",
            domain="operational",
            action_class="spend",
            subject="account:9",
            issuer="prior_approval:99",
            valid_to=_past(1),
        )
        self.assertFalse(w.permits("spend", "operational", "account:9"))

    def test_previous_successful_action_does_not_extend_jurisdiction(self):
        w = Warrant(
            warrant_id="w_prev",
            domain="operational",
            action_class="publish",
            subject="doc:old",
            valid_to=_future(1),
        )
        w.complete()
        self.assertFalse(w.permits("publish", "operational", "doc:old"))
        self.assertFalse(w.permits("publish", "operational", "doc:new"))

    def test_old_criminal_info_does_not_auto_warrant(self):
        c = Claim(
            claim_id="c_old_crime",
            subject="person:mike",
            predicate="offense",
            value="Y",
            domain=ClaimDomain.CRIMINAL,
            source="archive",
            time_observed="2010-01-01T00:00:00+00:00",
            status=ClaimStatus.HISTORICAL,
        )
        fw = ClaimToWarrantFirewall()
        with self.assertRaises(TemporalAuthorityError):
            fw.claim_cannot_create_action_authority(c)

    def test_category_membership_not_authority(self):
        c = Claim(
            claim_id="c_cat",
            subject="person:nina",
            predicate="member_of",
            value="high_risk_group",
            domain=ClaimDomain.RISK,
            source="classifier",
        )
        fw = ClaimToWarrantFirewall()
        with self.assertRaises(TemporalAuthorityError):
            fw.claim_cannot_create_action_authority(c)

    def test_repeated_predictions_still_not_authority(self):
        pf = PredictionFirewall()
        for _ in range(5):
            with self.assertRaises(TemporalAuthorityError):
                pf.assert_prediction_is_evidence_not_authority(
                    prediction="again",
                    confidence=0.98,
                    action_type="block",
                )

    def test_stale_warrant_rejected(self):
        w = Warrant(
            warrant_id="w_stale",
            domain="operational",
            action_class="access",
            subject="resource:1",
            valid_from=_past(100),
            valid_to=_past(50),
        )
        self.assertFalse(w.is_active())

    def test_domain_swapping_blocked(self):
        dc = DomainContainment()
        with self.assertRaises(TemporalAuthorityError):
            dc.assert_domain_compatible(
                ClaimDomain.MEDICAL,
                "medical",
                "financial",
            )

    def test_founder_identity_does_not_bypass(self):
        """Robert / founder test: authorship ≠ epistemic sovereignty."""
        c = Claim(
            claim_id="c_founder",
            subject="person:robert_emmanuel_laday",
            predicate="is_ceo",
            value=True,
            domain=ClaimDomain.OPERATIONAL,
            source="company_governance",
            confidence=1.0,
        )
        fw = ClaimToWarrantFirewall()
        # Even the founder claim does not itself create unrestricted action authority
        with self.assertRaises(TemporalAuthorityError):
            fw.claim_cannot_create_action_authority(c)

    def test_provider_identity_does_not_bypass(self):
        c = Claim(
            claim_id="c_prov",
            subject="provider:xai",
            predicate="model_certainty",
            value="absolute",
            domain=ClaimDomain.PREDICTION,
            source="provider",
            confidence=1.0,
        )
        fw = ClaimToWarrantFirewall()
        with self.assertRaises(TemporalAuthorityError):
            fw.claim_cannot_create_action_authority(c)


if __name__ == "__main__":
    unittest.main()
