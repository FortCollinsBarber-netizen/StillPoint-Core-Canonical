from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path

from stillpoint.temporal.envelope import (
    ClaimEnvelope,
    ClaimUseEvent,
    ClaimUseKind,
    ConditionOperator,
    ContinuationCondition,
    EpistemicReach,
    EvidenceContext,
    EvidenceEnvironment,
    EnvelopeStatus,
    MemoryPolicy,
    StandingState,
)
from stillpoint.temporal.envelope_store import ClaimEnvelopeStore


class Patch010ClaimEnvelopeTests(unittest.TestCase):
    def _operational(self, **overrides):
        data = dict(
            envelope_id="env-1",
            claim_id="claim-1",
            domain="communications",
            purpose="decide ordinary follow-up cadence",
            epistemic_reach=EpistemicReach(
                available_sources=["mailbox:stillpoint"],
                observed_variables=["reply_count", "last_reply_at"],
                inferred_variables=["engagement_state"],
                blind_spots=["offline conversations"],
            ),
            permitted_uses=["routine_followup"],
            prohibited_uses=["contract_commitment", "financial_commitment"],
            continuation_conditions=[
                ContinuationCondition("mailbox.id", ConditionOperator.EQ, "stillpoint"),
                ContinuationCondition("contact.class", ConditionOperator.IN, ["existing", "invited"]),
            ],
            correction_routes=["signal:correction_ingress"],
            release_conditions=["mailbox identity changes", "contact revokes consent"],
            reentry_requirements=["new present evidence", "new standing evaluation"],
            memory_policy=MemoryPolicy(purposes=["history", "accountability"]),
            operational=True,
        )
        data.update(overrides)
        return ClaimEnvelope(**data)

    def test_operational_envelope_requires_bounded_contract(self):
        with self.assertRaises(ValueError):
            self._operational(continuation_conditions=[])
        with self.assertRaises(ValueError):
            self._operational(correction_routes=[])
        with self.assertRaises(ValueError):
            self._operational(permitted_uses=["*"])

    def test_current_continuation_is_not_authority(self):
        envelope = self._operational()
        assessment = envelope.assess_continuation(
            facts={"mailbox": {"id": "stillpoint"}, "contact": {"class": "existing"}},
            proposed_use="routine_followup",
        )
        self.assertEqual(assessment.state, StandingState.CURRENT)
        self.assertTrue(assessment.continuation_satisfied)
        self.assertIn("separate warrant still required", assessment.note)
        self.assertFalse(hasattr(envelope, "authorize"))
        self.assertFalse(hasattr(envelope, "mint_warrant"))

    def test_missing_or_changed_condition_fails_closed_to_review(self):
        envelope = self._operational()
        missing = envelope.assess_continuation(
            facts={"mailbox": {"id": "stillpoint"}}, proposed_use="routine_followup"
        )
        self.assertEqual(missing.state, StandingState.REVIEW_REQUIRED)
        self.assertTrue(any("missing:contact.class" == reason for reason in missing.failed_conditions))

        changed = envelope.assess_continuation(
            facts={"mailbox": {"id": "other"}, "contact": {"class": "existing"}},
            proposed_use="routine_followup",
        )
        self.assertEqual(changed.state, StandingState.REVIEW_REQUIRED)

    def test_historical_envelope_is_former_not_false(self):
        envelope = self._operational(status=EnvelopeStatus.HISTORICAL)
        assessment = envelope.assess_continuation(
            facts={"mailbox": {"id": "stillpoint"}, "contact": {"class": "existing"}},
            proposed_use="routine_followup",
        )
        self.assertEqual(assessment.state, StandingState.FORMER)
        self.assertIn("historically preserved", assessment.note)

    def test_memory_cannot_be_declared_reauthorization(self):
        with self.assertRaises(ValueError):
            MemoryPolicy(operational_reauthorization=True)

    def test_operational_and_intervention_use_require_action_and_warrant(self):
        with self.assertRaises(ValueError):
            ClaimUseEvent(
                use_id="use-1",
                claim_id="claim-1",
                envelope_id="env-1",
                use_kind=ClaimUseKind.OPERATIONAL,
                actor="signal",
                purpose="follow up",
            )
        with self.assertRaises(ValueError):
            ClaimUseEvent(
                use_id="use-2",
                claim_id="claim-1",
                envelope_id="env-1",
                use_kind=ClaimUseKind.INTERVENTION,
                actor="signal",
                purpose="reduce cadence",
                warrant_id="w-1",
                action_id="a-1",
            )
        event = ClaimUseEvent(
            use_id="use-3",
            claim_id="claim-1",
            envelope_id="env-1",
            use_kind=ClaimUseKind.INTERVENTION,
            actor="signal",
            purpose="reduce cadence",
            warrant_id="w-1",
            action_id="a-1",
            intervention_effects=["reduced_followup_frequency"],
        )
        self.assertEqual(event.use_kind, ClaimUseKind.INTERVENTION)

    def test_post_intervention_evidence_requires_prior_use_linkage(self):
        with self.assertRaises(ValueError):
            EvidenceContext(
                evidence_id="e-1",
                environment=EvidenceEnvironment.POST_INTERVENTION,
            )
        context = EvidenceContext(
            evidence_id="e-2",
            environment=EvidenceEnvironment.POST_INTERVENTION,
            prior_use_ids=["use-3"],
            system_influence=["followup_frequency_reduced"],
        )
        self.assertFalse(context.independent_of_prior_system_use)


class Patch010MigrationTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(
            """
            CREATE TABLE temporal_claims (claim_id TEXT PRIMARY KEY);
            CREATE TABLE temporal_warrants (warrant_id TEXT PRIMARY KEY);
            CREATE TABLE action_requests (id TEXT PRIMARY KEY);
            CREATE TABLE temporal_evidence (evidence_id TEXT PRIMARY KEY);
            INSERT INTO temporal_claims VALUES ('claim-1');
            INSERT INTO temporal_warrants VALUES ('w-1');
            INSERT INTO action_requests VALUES ('a-1');
            INSERT INTO temporal_evidence VALUES ('e-1');
            """
        )
        migration = Path(__file__).resolve().parents[1] / "migrations" / "011_claim_envelope_continuing_evidence.sql"
        self.conn.executescript(migration.read_text(encoding="utf-8"))

    def tearDown(self):
        self.conn.close()

    def _insert_envelope(self, *, envelope_id="env-1", operational=1, continuation='["mailbox"]'):
        self.conn.execute(
            """INSERT INTO temporal_claim_envelopes
            (envelope_id,claim_id,domain,purpose,epistemic_reach_json,permitted_uses_json,
             prohibited_uses_json,continuation_conditions_json,correction_routes_json,
             release_conditions_json,reentry_requirements_json,memory_policy_json,
             memory_may_reauthorize,operational,status,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                envelope_id,"claim-1","communications","followup","{\"sources\":[\"mailbox\"]}",
                '["routine_followup"]','[]',continuation,'["correction"]','["release"]',
                '["new evidence"]','{\"purposes\":[\"history\"]}',0,operational,"active",
                "2026-09-17T16:00:00+00:00","2026-09-17T16:00:00+00:00",
            ),
        )

    def test_db_rejects_operational_envelope_without_continuation(self):
        with self.assertRaises(sqlite3.DatabaseError):
            self._insert_envelope(continuation="[]")
        self.conn.rollback()

    def test_db_rejects_memory_as_reauthorization(self):
        with self.assertRaises(sqlite3.DatabaseError):
            self.conn.execute(
                """INSERT INTO temporal_claim_envelopes
                (envelope_id,claim_id,domain,purpose,epistemic_reach_json,permitted_uses_json,
                 continuation_conditions_json,correction_routes_json,release_conditions_json,
                 reentry_requirements_json,memory_may_reauthorize,operational,status,created_at,updated_at)
                VALUES('env-x','claim-1','d','p','{}','[]','[]','[]','[]','[]',1,0,'active','t','t')"""
            )
        self.conn.rollback()

    def test_operational_use_requires_bound_warrant_and_action(self):
        self._insert_envelope()
        self.conn.commit()
        with self.assertRaises(sqlite3.DatabaseError):
            self.conn.execute(
                """INSERT INTO temporal_claim_use_events
                (use_id,claim_id,envelope_id,use_kind,actor,purpose,occurred_at)
                VALUES('u-bad','claim-1','env-1','operational','signal','followup','t')"""
            )
        self.conn.rollback()
        self.conn.execute(
            """INSERT INTO temporal_claim_use_events
            (use_id,claim_id,envelope_id,use_kind,actor,purpose,occurred_at,warrant_id,action_id)
            VALUES('u-1','claim-1','env-1','operational','signal','followup','t','w-1','a-1')"""
        )

    def test_use_history_and_evidence_context_are_append_only(self):
        self._insert_envelope()
        self.conn.execute(
            """INSERT INTO temporal_claim_use_events
            (use_id,claim_id,envelope_id,use_kind,actor,purpose,occurred_at,warrant_id,action_id,
             intervention_effects_json)
            VALUES('u-1','claim-1','env-1','intervention','signal','reduce cadence','t','w-1','a-1',
                   '["reduced_frequency"]')"""
        )
        self.conn.execute(
            """INSERT INTO temporal_evidence_contexts
            (evidence_id,environment,prior_use_ids_json,system_influence_json,recorded_at)
            VALUES('e-1','post_intervention','["u-1"]','["reduced_frequency"]','t')"""
        )
        self.conn.commit()
        with self.assertRaises(sqlite3.DatabaseError):
            self.conn.execute("UPDATE temporal_claim_use_events SET purpose='changed' WHERE use_id='u-1'")
        self.conn.rollback()
        with self.assertRaises(sqlite3.DatabaseError):
            self.conn.execute("DELETE FROM temporal_evidence_contexts WHERE evidence_id='e-1'")
        self.conn.rollback()


class _DBWrapper:
    def __init__(self, conn):
        self.conn = conn
    def _connection(self):
        return self.conn


class Patch010StoreTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(
            """
            CREATE TABLE temporal_claims (claim_id TEXT PRIMARY KEY);
            CREATE TABLE temporal_warrants (warrant_id TEXT PRIMARY KEY);
            CREATE TABLE action_requests (id TEXT PRIMARY KEY);
            CREATE TABLE temporal_evidence (evidence_id TEXT PRIMARY KEY);
            INSERT INTO temporal_claims VALUES ('claim-1');
            INSERT INTO temporal_warrants VALUES ('w-1');
            INSERT INTO action_requests VALUES ('a-1');
            INSERT INTO temporal_evidence VALUES ('e-1');
            """
        )
        migration = Path(__file__).resolve().parents[1] / "migrations" / "011_claim_envelope_continuing_evidence.sql"
        self.conn.executescript(migration.read_text(encoding="utf-8"))
        self.store = ClaimEnvelopeStore(_DBWrapper(self.conn))

    def tearDown(self):
        self.conn.close()

    def _envelope(self, envelope_id="env-1"):
        return ClaimEnvelope(
            envelope_id=envelope_id,
            claim_id="claim-1",
            domain="communications",
            purpose="routine followup",
            epistemic_reach=EpistemicReach(available_sources=["mailbox"], blind_spots=["offline"]),
            permitted_uses=["routine_followup"],
            continuation_conditions=[ContinuationCondition("mailbox.id", ConditionOperator.EQ, "stillpoint")],
            correction_routes=["signal:correction"],
            release_conditions=["mailbox changes"],
            reentry_requirements=["new evidence"],
            operational=True,
        )

    def test_store_round_trip_and_supersession_preserve_former_state(self):
        first = self._envelope("env-1")
        self.store.persist(first)
        loaded = self.store.get_active_for_claim("claim-1")
        self.assertEqual(loaded.to_dict(), first.to_dict())

        second = self._envelope("env-2")
        self.store.supersede("env-1", second)
        old = self.store.get("env-1")
        current = self.store.get_active_for_claim("claim-1")
        self.assertEqual(old.status, EnvelopeStatus.SUPERSEDED)
        self.assertEqual(current.envelope_id, "env-2")
        self.assertEqual(current.supersedes_envelope_id, "env-1")

    def test_store_records_intervention_and_post_intervention_context(self):
        self.store.persist(self._envelope())
        use = ClaimUseEvent(
            use_id="use-1", claim_id="claim-1", envelope_id="env-1",
            use_kind=ClaimUseKind.INTERVENTION, actor="signal", purpose="reduce cadence",
            warrant_id="w-1", action_id="a-1", intervention_effects=["reduced_frequency"],
        )
        self.store.record_use(use)
        self.store.record_evidence_context(EvidenceContext(
            evidence_id="e-1", environment=EvidenceEnvironment.POST_INTERVENTION,
            prior_use_ids=["use-1"], system_influence=["reduced_frequency"],
        ))
        self.assertEqual(self.store.list_uses("claim-1")[0]["use_kind"], "intervention")


if __name__ == "__main__":
    unittest.main()
