from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path

from stillpoint.authority.standing import (
    DelegationStanding,
    DelegationStatus,
    StandingDelegation,
)
from stillpoint.authority.standing_store import StandingDelegationStore
from stillpoint.temporal.envelope import (
    ClaimEnvelope,
    ConditionOperator,
    ContinuationCondition,
    EpistemicReach,
    EnvelopeStatus,
)


T0 = "2026-09-17T16:00:00+00:00"
T1 = "2026-09-18T16:00:00+00:00"
T2 = "2026-10-01T16:00:00+00:00"


def signal_envelope(status=EnvelopeStatus.ACTIVE):
    return ClaimEnvelope(
        envelope_id="env-signal",
        claim_id="claim-mailbox-context",
        domain="communications",
        purpose="ordinary StillPoint correspondence",
        epistemic_reach=EpistemicReach(
            available_sources=["mailbox:stillpoint"],
            blind_spots=["offline conversations"],
        ),
        permitted_uses=["routine_email"],
        continuation_conditions=[
            ContinuationCondition("mailbox.id", ConditionOperator.EQ, "stillpoint")
        ],
        correction_routes=["signal:correction"],
        release_conditions=["mailbox identity changes"],
        reentry_requirements=["new present evidence"],
        operational=True,
        status=status,
    )


def signal_delegation(**overrides):
    data = dict(
        delegation_id="del-signal-email",
        delegate_role="signal",
        issuer="CEO:Robert Emmanuel LaDay",
        policy_basis="CEO standing delegation",
        purpose="ordinary business email",
        claim_envelope_ids=["env-signal"],
        allowed_action_types=["send_email"],
        continuation_conditions=[
            ContinuationCondition("company.policy_revision", ConditionOperator.EQ, "rev-1"),
            ContinuationCondition("mailbox.id", ConditionOperator.EQ, "stillpoint"),
        ],
        execution_conditions=[
            ContinuationCondition("recipient.class", ConditionOperator.IN, ["existing", "invited"]),
            ContinuationCondition("content.contractual", ConditionOperator.EQ, False),
            ContinuationCondition("content.money_commitment", ConditionOperator.EQ, False),
        ],
        exclusions=["contracts", "money", "legal representations"],
        release_conditions=["policy revision changes", "mailbox identity changes", "CEO revocation"],
        valid_from=T0,
        review_by=T2,
    )
    data.update(overrides)
    return StandingDelegation(**data)


class Patch011StandingDelegationTests(unittest.TestCase):
    def _assess(self, delegation=None, envelope=None, **changes):
        delegation = delegation or signal_delegation()
        envelope = envelope or signal_envelope()
        continuation = {
            "company": {"policy_revision": "rev-1"},
            "mailbox": {"id": "stillpoint"},
        }
        execution = {
            "recipient": {"class": "existing"},
            "content": {"contractual": False, "money_commitment": False},
        }
        continuation.update(changes.pop("continuation", {}))
        execution.update(changes.pop("execution", {}))
        return delegation.assess(
            now_iso=changes.pop("now_iso", T1),
            continuation_facts=continuation,
            action_type=changes.pop("action_type", "send_email"),
            execution_facts=execution,
            envelopes={"env-signal": envelope},
            envelope_facts={"env-signal": {"mailbox": {"id": "stillpoint"}}},
            proposed_use_by_envelope={"env-signal": "routine_email"},
        )

    def test_current_delegation_is_only_warrant_eligibility(self):
        delegation = signal_delegation()
        result = self._assess(delegation=delegation)
        self.assertEqual(result.standing, DelegationStanding.CURRENT)
        self.assertTrue(result.eligible_for_warrant_consideration)
        self.assertIn("separate execution-warrant", result.note)
        self.assertFalse(hasattr(delegation, "mint_warrant"))
        self.assertFalse(hasattr(delegation, "authorize_action"))

    def test_missing_present_fact_fails_closed(self):
        delegation = signal_delegation()
        result = delegation.assess(
            now_iso=T1,
            continuation_facts={"mailbox": {"id": "stillpoint"}},
            action_type="send_email",
            execution_facts={
                "recipient": {"class": "existing"},
                "content": {"contractual": False, "money_commitment": False},
            },
            envelopes={"env-signal": signal_envelope()},
            envelope_facts={"env-signal": {"mailbox": {"id": "stillpoint"}}},
            proposed_use_by_envelope={"env-signal": "routine_email"},
        )
        self.assertEqual(result.standing, DelegationStanding.REVIEW_REQUIRED)
        self.assertIn("missing:company.policy_revision", result.failed_conditions)

    def test_former_supporting_envelope_blocks_delegation(self):
        result = self._assess(envelope=signal_envelope(status=EnvelopeStatus.HISTORICAL))
        self.assertEqual(result.standing, DelegationStanding.REVIEW_REQUIRED)
        self.assertIn("envelope_not_current:env-signal", result.failed_conditions)

    def test_money_or_contract_action_fails_execution_scope(self):
        delegation = signal_delegation()
        result = delegation.assess(
            now_iso=T1,
            continuation_facts={"company": {"policy_revision": "rev-1"}, "mailbox": {"id": "stillpoint"}},
            action_type="send_email",
            execution_facts={
                "recipient": {"class": "existing"},
                "content": {"contractual": True, "money_commitment": False},
            },
            envelopes={"env-signal": signal_envelope()},
            envelope_facts={"env-signal": {"mailbox": {"id": "stillpoint"}}},
            proposed_use_by_envelope={"env-signal": "routine_email"},
        )
        self.assertEqual(result.standing, DelegationStanding.REVIEW_REQUIRED)
        self.assertTrue(any("content.contractual" in f for f in result.failed_conditions))

    def test_review_boundary_does_not_auto_renew(self):
        result = self._assess(now_iso=T2)
        self.assertEqual(result.standing, DelegationStanding.REVIEW_REQUIRED)
        self.assertIn("delegation_review_due", result.failed_conditions)

    def test_revoked_delegation_is_former(self):
        result = self._assess(delegation=signal_delegation(status=DelegationStatus.REVOKED))
        self.assertEqual(result.standing, DelegationStanding.FORMER)

    def test_unbounded_action_wildcard_is_rejected(self):
        with self.assertRaises(ValueError):
            signal_delegation(allowed_action_types=["*"])


class _DBWrapper:
    def __init__(self, conn):
        self.conn = conn
    def _connection(self):
        return self.conn


class Patch011StandingStoreTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("CREATE TABLE action_requests (id TEXT PRIMARY KEY)")
        self.conn.execute("INSERT INTO action_requests VALUES ('action-1')")
        migration = Path(__file__).resolve().parents[1] / "migrations" / "012_standing_delegation.sql"
        self.conn.executescript(migration.read_text(encoding="utf-8"))
        self.store = StandingDelegationStore(_DBWrapper(self.conn))

    def tearDown(self):
        self.conn.close()

    def test_store_round_trip_and_append_only_evaluation(self):
        delegation = signal_delegation()
        self.store.persist(delegation)
        loaded = self.store.get(delegation.delegation_id)
        self.assertEqual(loaded.to_dict(), delegation.to_dict())
        assessment = delegation.assess(
            now_iso=T1,
            continuation_facts={"company": {"policy_revision": "rev-1"}, "mailbox": {"id": "stillpoint"}},
            action_type="send_email",
            execution_facts={"recipient": {"class": "existing"}, "content": {"contractual": False, "money_commitment": False}},
            envelopes={"env-signal": signal_envelope()},
            envelope_facts={"env-signal": {"mailbox": {"id": "stillpoint"}}},
            proposed_use_by_envelope={"env-signal": "routine_email"},
        )
        evaluation_id = self.store.record_assessment(
            delegation_id=delegation.delegation_id,
            assessment=assessment,
            evaluated_at=T1,
            continuation_facts={"company": {"policy_revision": "rev-1"}},
            execution_facts={"recipient": {"class": "existing"}},
            action_id="action-1",
            action_type="send_email",
            action_target="person@example.com",
        )
        with self.assertRaises(sqlite3.DatabaseError):
            self.conn.execute(
                "UPDATE standing_delegation_evaluations SET result='former' WHERE evaluation_id=?",
                (evaluation_id,),
            )
        self.conn.rollback()

    def test_database_rejects_empty_standing_scope(self):
        with self.assertRaises(sqlite3.DatabaseError):
            self.conn.execute(
                """INSERT INTO standing_delegations
                (delegation_id,delegate_role,issuer,policy_basis,purpose,claim_envelope_ids_json,
                 allowed_action_types_json,continuation_conditions_json,execution_conditions_json,
                 release_conditions_json,valid_from,review_by,status,created_at,updated_at)
                VALUES('d','signal','CEO','basis','purpose','[]','[]','[]','[]','[]',?,?,?,?,?)""",
                (T0,T2,'active',T0,T0),
            )


if __name__ == "__main__":
    unittest.main()
