from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from stillpoint.temporal.evidence import EvidenceEvent, EvidenceKind
from stillpoint.temporal.lifecycle import (
    assert_bounded_reentry,
    build_action_release,
    build_reevaluation_trigger,
    old_authority_never_reactivates,
)
from stillpoint.temporal.warrants import Warrant, WarrantStatus
from stillpoint.temporal.firewall import TemporalAuthorityError


def consumed_warrant(warrant_id="old-warrant"):
    now=datetime.now(timezone.utc)
    return Warrant(
        warrant_id=warrant_id,
        domain="publishing",
        action_class="publish",
        subject="task:t1",
        target="public",
        issuer="CEO:Robert Emmanuel LaDay",
        policy_basis="explicit_ceo_approval:a1",
        valid_from=(now-timedelta(minutes=5)).isoformat(),
        valid_to=(now+timedelta(minutes=5)).isoformat(),
        status=WarrantStatus.COMPLETED,
        scope={"authority_revision":"r1"},
    )


def new_warrant(warrant_id="new-warrant"):
    now=datetime.now(timezone.utc)
    return Warrant(
        warrant_id=warrant_id,
        domain="publishing",
        action_class="publish",
        subject="task:t1",
        target="public",
        issuer="CEO:Robert Emmanuel LaDay",
        policy_basis="reevaluation:new-evidence",
        valid_from=(now-timedelta(seconds=1)).isoformat(),
        valid_to=(now+timedelta(minutes=5)).isoformat(),
        status=WarrantStatus.ACTIVE,
        scope={"authority_revision":"r2"},
    )


class LifecycleTests(unittest.TestCase):
    def test_release_records_completed_authority_without_reactivating_it(self):
        old=consumed_warrant()
        release=build_action_release(
            action_id="action1",
            warrant=old,
            reason="dispatch_terminal:completed",
        )
        self.assertEqual(release.prior_warrant_id,old.warrant_id)
        self.assertFalse(release.restores_access)
        self.assertFalse(release.erases_consequences)
        self.assertEqual(old.status,WarrantStatus.COMPLETED)

    def test_release_rejects_active_warrant(self):
        active=new_warrant()
        with self.assertRaises(TemporalAuthorityError):
            build_action_release(
                action_id="a",
                warrant=active,
                reason="too-early",
            )

    def test_reevaluation_requires_new_evidence(self):
        old=consumed_warrant()
        with self.assertRaises(ValueError):
            build_reevaluation_trigger(
                prior_disposition="completed",
                prior_action_id="a1",
                prior_warrant=old,
                evidence=[],
                reason="none",
            )

    def test_reevaluation_subject_must_match(self):
        old=consumed_warrant()
        event=EvidenceEvent(
            evidence_id="e1",
            kind=EvidenceKind.CORRECTION,
            subject="task:other",
            content={"changed":True},
            source="test",
        )
        with self.assertRaises(TemporalAuthorityError):
            build_reevaluation_trigger(
                prior_disposition="completed",
                prior_action_id="a1",
                prior_warrant=old,
                evidence=[event],
                reason="new fact",
            )

    def test_reentry_requires_new_warrant_id(self):
        old=consumed_warrant()
        event=EvidenceEvent(
            evidence_id="e1",
            kind=EvidenceKind.CORRECTION,
            subject="task:t1",
            content={"changed":True},
            source="test",
        )
        trigger=build_reevaluation_trigger(
            prior_disposition="completed",
            prior_action_id="a1",
            prior_warrant=old,
            evidence=[event],
            reason="new fact",
        )
        candidate=new_warrant(warrant_id=old.warrant_id)
        with self.assertRaises(TemporalAuthorityError):
            assert_bounded_reentry(
                prior_warrant=old,
                candidate_warrant=candidate,
                trigger=trigger,
            )

    def test_reentry_with_new_evidence_and_new_warrant_is_allowed(self):
        old=consumed_warrant()
        event=EvidenceEvent(
            evidence_id="e1",
            kind=EvidenceKind.CORRECTION,
            subject="task:t1",
            content={"changed":True},
            source="test",
        )
        trigger=build_reevaluation_trigger(
            prior_disposition="completed",
            prior_action_id="a1",
            prior_warrant=old,
            evidence=[event],
            reason="new fact",
        )
        assert_bounded_reentry(
            prior_warrant=old,
            candidate_warrant=new_warrant(),
            trigger=trigger,
        )

    def test_old_authority_cannot_reactivate(self):
        old=consumed_warrant()
        old_authority_never_reactivates(old)
        active=new_warrant()
        with self.assertRaises(TemporalAuthorityError):
            old_authority_never_reactivates(active)


if __name__=="__main__":
    unittest.main()
