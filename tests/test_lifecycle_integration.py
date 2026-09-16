"""Patch 004 integration tests — atomic auth, release, reentry, invariants."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from stillpoint.adapters.registry import ActionAdapterRegistry
from stillpoint.contracts.models import ActionEvidence, ActionResult
from stillpoint.db import CompanyDB
from stillpoint.registry import AgentRegistry
from stillpoint.runtime import CompanyRuntime
from stillpoint.temporal.evidence import EvidenceEvent, EvidenceKind
from stillpoint.temporal.warrants import Warrant, WarrantStatus
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[1]


class MockProvider:
    default_model = "mock"
    def generate(self, **kw):
        return type("R", (), {"text": "ok"})()


class RealAdapter:
    name = "real-smtp"
    action_types = ("send_email", "publish", "other_external")
    def can_execute(self, request): return True
    def execute(self, request):
        c = request.success_criteria[0]
        return ActionResult(
            action_id=request.action_id, status="succeeded",
            evidence=[ActionEvidence(type=c, sha256="x", satisfies=c)],
            adapter=self.name, external_id="ext-1",
        )


class RaisingAdapter:
    name = "raise-smtp"
    action_types = ("send_email", "publish", "other_external")
    def can_execute(self, request): return True
    def execute(self, request):
        raise RuntimeError("post-effect failure")


class LifecycleIntegrationTests(unittest.TestCase):
    def make(self, tmp: Path) -> CompanyRuntime:
        return CompanyRuntime(
            root=tmp, db=CompanyDB(tmp / "db.sqlite"),
            registry=AgentRegistry(ROOT / "config" / "agents.json"),
            provider=MockProvider(), default_model="mock", smart_routing=False,
        )

    def _approve_action(self, rt):
        out = rt.submit("Send this note to the printer.")
        rt.approve(out.task_id)
        action = rt.db.list_action_requests(out.task_id)[0]
        return out.task_id, action

    # 1. ATOMIC CEO AUTHORIZATION — rollback on failure
    def test_atomic_authorize_rolls_back_on_failure(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            rt = self.make(tmp)
            out = rt.submit("Send this note to the printer.")
            task_id = out.task_id
            actions = [r for r in rt.db.list_action_requests(task_id) if r["status"] == "waiting_approval"]
            self.assertTrue(actions)
            # Force failure: pass empty bindings
            with self.assertRaises(ValueError):
                rt.db.authorize_actions_atomically(
                    task_id=task_id, approval_id="bad", approval_note="", bindings=[],
                )
            # task still waiting; no warrants
            task = rt.db.get_task(task_id)
            self.assertEqual(task["status"], "waiting_approval")
            for a in rt.db.list_action_requests(task_id):
                self.assertIsNone(a.get("warrant_id") or None)
                self.assertEqual(a["status"], "waiting_approval")
            # Successful atomic approve
            rt.approve(task_id)
            task = rt.db.get_task(task_id)
            self.assertEqual(task["status"], "ready_for_action")
            for a in rt.db.list_action_requests(task_id):
                self.assertTrue(a.get("warrant_id"))
                self.assertEqual(a["status"], "ready_for_action")
            rt.db.close()

    # 2. READY-STATE DB INVARIANT
    def test_ready_without_warrant_rejected_by_trigger(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            rt = self.make(tmp)
            out = rt.submit("Send this note to the printer.")
            action = rt.db.list_action_requests(out.task_id)[0]
            conn = rt.db._connection()
            with self.assertRaises(Exception):
                conn.execute(
                    "UPDATE action_requests SET status='ready_for_action' WHERE id=?",
                    (action["id"],),
                )
                conn.commit()
            rt.db.close()

    # 3. TERMINAL DISPATCH RELEASE
    def test_completed_dispatch_creates_release(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            rt = self.make(tmp)
            _, action = self._approve_action(rt)
            out = rt.execute_action(action["id"], ActionAdapterRegistry([RealAdapter()]))
            self.assertEqual(out["status"], "completed")
            release = rt.db.get_temporal_release_for_action(action["id"])
            self.assertIsNotNone(release)
            self.assertEqual(release["prior_warrant_id"], action["warrant_id"] if "warrant_id" in action else rt.db.get_action_request(action["id"])["warrant_id"])
            row = rt.db.get_action_request(action["id"])
            self.assertEqual(row["release_id"], release["release_id"])
            w = rt.db.get_temporal_warrant(row["warrant_id"])
            self.assertEqual(w.status.value, "completed")
            rt.db.close()

    # 4. UNCERTAIN — no release until reconciliation
    def test_uncertain_has_no_release_until_reconcile(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            rt = self.make(tmp)
            _, action = self._approve_action(rt)
            with self.assertRaises(RuntimeError):
                rt.execute_action(action["id"], ActionAdapterRegistry([RaisingAdapter()]))
            self.assertIsNone(rt.db.get_temporal_release_for_action(action["id"]))
            row = rt.db.get_action_request(action["id"])
            w = rt.db.get_temporal_warrant(row["warrant_id"])
            self.assertEqual(w.status.value, "completed")
            rt.reconcile_action_dispatch(action["id"], effect_occurred=False, note="no effect")
            release = rt.db.get_temporal_release_for_action(action["id"])
            self.assertIsNotNone(release)
            w2 = rt.db.get_temporal_warrant(row["warrant_id"])
            self.assertEqual(w2.status.value, "completed")
            rt.db.close()

    # 5. CONTINUING EVIDENCE
    def test_continuing_evidence_and_reevaluation(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            rt = self.make(tmp)
            _, action = self._approve_action(rt)
            rt.execute_action(action["id"], ActionAdapterRegistry([RealAdapter()]))
            row = rt.db.get_action_request(action["id"])
            release_before = row["release_id"]
            event = EvidenceEvent(
                evidence_id="",
                kind=EvidenceKind.CORRECTION,
                subject=f"task:{row['task_id']}",
                content={"note": "new material fact"},
                source="test",
            )
            # subject must match warrant subject = task:<task_id>
            w = rt.db.get_temporal_warrant(row["warrant_id"])
            event = EvidenceEvent(
                evidence_id="",
                kind=EvidenceKind.CORRECTION,
                subject=w.subject,
                content={"note": "new material fact"},
                source="test",
            )
            trigger = rt.record_new_evidence_for_action(action["id"], [event])
            self.assertTrue(trigger.trigger_id)
            self.assertTrue(trigger.new_evidence_ids)
            row2 = rt.db.get_action_request(action["id"])
            self.assertEqual(row2["release_id"], release_before)
            self.assertEqual(row2["reevaluation_trigger_id"], trigger.trigger_id)
            rt.db.close()

    # 6-8. REENTRY bounds
    def test_reentry_requires_new_warrant_and_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            rt = self.make(tmp)
            _, action = self._approve_action(rt)
            rt.execute_action(action["id"], ActionAdapterRegistry([RealAdapter()]))
            row = rt.db.get_action_request(action["id"])
            w = rt.db.get_temporal_warrant(row["warrant_id"])
            event = EvidenceEvent(
                evidence_id="", kind=EvidenceKind.CORRECTION,
                subject=w.subject, content={"x": 1}, source="test",
            )
            trigger = rt.record_new_evidence_for_action(action["id"], [event])
            # create a second waiting action for reentry target
            out2 = rt.submit("Send this note to the printer.")
            # get a new waiting action
            new_actions = [r for r in rt.db.list_action_requests(out2.task_id) if r["status"] == "waiting_approval"]
            self.assertTrue(new_actions)
            new_id = new_actions[0]["id"]
            # old warrant rejected
            from stillpoint.temporal.firewall import TemporalAuthorityError
            with self.assertRaises(TemporalAuthorityError):
                rt.authorize_reentry(
                    prior_action_id=action["id"],
                    new_action_id=new_id,
                    candidate_warrant=w,
                    reevaluation_trigger=trigger,
                )
            # new active warrant with same subject allowed after approve path would issue it
            now = datetime.now(timezone.utc)
            candidate = Warrant(
                warrant_id="",
                domain=w.domain,
                action_class=w.action_class,
                subject=w.subject,
                target=w.target,
                issuer="CEO:Robert Emmanuel LaDay",
                policy_basis="reevaluation:new",
                valid_from=(now - timedelta(seconds=1)).isoformat(),
                valid_to=(now + timedelta(minutes=10)).isoformat(),
                status=WarrantStatus.ACTIVE,
                scope={"authority_revision": "r-new", "max_actions": 1},
            )
            # new action still waiting - bind via authorize_reentry
            bound = rt.authorize_reentry(
                prior_action_id=action["id"],
                new_action_id=new_id,
                candidate_warrant=candidate,
                reevaluation_trigger=trigger,
            )
            self.assertEqual(bound["reentry_parent_action_id"], action["id"])
            self.assertEqual(bound["reevaluation_trigger_id"], trigger.trigger_id)
            self.assertNotEqual(bound["warrant_id"], row["warrant_id"])
            # prior release unchanged
            self.assertEqual(
                rt.db.get_action_request(action["id"])["release_id"],
                row["release_id"],
            )
            rt.db.close()

    def test_reentry_without_evidence_denied(self):
        from stillpoint.temporal.lifecycle import assert_bounded_reentry
        from stillpoint.temporal.reentry import ReevaluationTrigger
        from stillpoint.temporal.firewall import TemporalAuthorityError
        now = datetime.now(timezone.utc)
        old = Warrant(
            warrant_id="old", domain="publishing", action_class="publish",
            subject="task:t1", target="public", issuer="CEO:x",
            policy_basis="p", valid_from=now.isoformat(),
            valid_to=(now + timedelta(minutes=5)).isoformat(),
            status=WarrantStatus.COMPLETED,
        )
        candidate = Warrant(
            warrant_id="new", domain="publishing", action_class="publish",
            subject="task:t1", target="public", issuer="CEO:x",
            policy_basis="p2", valid_from=now.isoformat(),
            valid_to=(now + timedelta(minutes=5)).isoformat(),
            status=WarrantStatus.ACTIVE,
        )
        trigger = ReevaluationTrigger(
            trigger_id="t1", prior_disposition="completed",
            prior_warrant_id="old", new_evidence_ids=[],
        )
        with self.assertRaises(TemporalAuthorityError):
            assert_bounded_reentry(
                prior_warrant=old, candidate_warrant=candidate, trigger=trigger,
            )


if __name__ == "__main__":
    unittest.main()
