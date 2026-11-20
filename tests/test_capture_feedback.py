"""Offline trust-boundary tests for the Capture77/Core advisory adapter."""
import copy
import unittest

from stillpoint.capture_feedback import FeedbackIntakeError, intake_feedback


CASE = "case-abc"
DIGEST = "a" * 64


def payload(verdict="uncertain", route="human_review_recommended"):
    return {
        "case_id": CASE, "case_revision": 7, "evidence_sha256": DIGEST,
        "authority": "read_only_no_dispatch_no_approval",
        "qualification": "operator_asserted_unverified",
        "observation_count": 1, "active_observation_count": 1,
        "stale_active_count": 0, "human_review_recommended": True,
        "suggested_route": route,
        "active_observations": [{
            "id": 4, "case_id": CASE, "witnessed_revision": 7,
            "evidence_sha256": DIGEST,
            "observer_provenance": "operator_asserted_unverified",
            "verdict": verdict, "next_action": "human_review",
        }],
    }


def ingest(data):
    return intake_feedback(
        data, expected_case_id=CASE, expected_revision=7,
        expected_evidence_sha256=DIGEST,
    )


class FeedbackBoundaryTests(unittest.TestCase):
    def test_human_review_is_advisory_only(self):
        data = payload()
        untouched = copy.deepcopy(data)
        result = ingest(data)
        self.assertEqual(data, untouched)
        self.assertEqual(result.recommended_route, "human_review_recommended")
        self.assertTrue(result.requires_human_attention)
        self.assertEqual(result.authority, "advisory_only_no_warrants")
        self.assertFalse(hasattr(result, "approve"))
        self.assertFalse(hasattr(result, "dispatch"))

    def test_forged_authority_and_stale_external_snapshot_rejected(self):
        for patch in [
            {"case_id": "wrong"},
            {"case_revision": 8},
            {"evidence_sha256": "b" * 64},
            {"authority": "may_dispatch"},
            {"qualification": "publisher_verified"},
            {"human_review_recommended": False},
            {"suggested_route": "routine_read_only"},
            {"active_observation_count": 4},
        ]:
            with self.subTest(patch=patch):
                data = payload()
                data.update(patch)
                with self.assertRaises(FeedbackIntakeError):
                    ingest(data)

    def test_recompute_freshness_from_independent_expected_snapshot(self):
        data = payload()
        data["active_observations"][0]["witnessed_revision"] = 6
        data["stale_active_count"] = 1
        data["human_review_recommended"] = False
        data["suggested_route"] = "reobserve_stale_evidence"
        result = ingest(data)
        self.assertEqual(result.stale_count, 1)
        self.assertFalse(result.requires_human_attention)
        self.assertEqual(result.recommended_route, "reobserve_stale_evidence")

    def test_conflicting_notes_remain_visible_not_consensus(self):
        data = payload()
        data["active_observations"].append({
            "id": 5, "case_id": CASE, "witnessed_revision": 7,
            "evidence_sha256": DIGEST,
            "observer_provenance": "operator_asserted_unverified",
            "verdict": "supports", "next_action": "no_change",
        })
        data["observation_count"] = 2
        data["active_observation_count"] = 2
        result = ingest(data)
        self.assertEqual(result.active_count, 2)
        self.assertEqual(result.recommended_route, "human_review_recommended")

    def test_observer_credential_and_duplicate_id_forgery_rejected(self):
        for patch in [
            {"observer_provenance": "authenticated"},
            {"case_id": "foreign"},
            {"verdict": "verified"},
            {"witnessed_revision": True},
        ]:
            with self.subTest(patch=patch):
                data = payload()
                data["active_observations"][0].update(patch)
                with self.assertRaises(FeedbackIntakeError):
                    ingest(data)
        data = payload()
        data["active_observations"].append(copy.deepcopy(data["active_observations"][0]))
        data["observation_count"] = 2
        data["active_observation_count"] = 2
        with self.assertRaises(FeedbackIntakeError):
            ingest(data)

    def test_zero_feedback_does_not_imply_approval(self):
        data = payload()
        data.update(observation_count=0, active_observation_count=0,
                    active_observations=[], stale_active_count=0,
                    human_review_recommended=False,
                    suggested_route="no_observation_yet")
        result = ingest(data)
        self.assertEqual(result.recommended_route, "no_observation_yet")
        self.assertFalse(result.requires_human_attention)


if __name__ == "__main__":
    unittest.main()
