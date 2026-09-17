from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from stillpoint.db import CompanyDB
from stillpoint.workers import (
    DurableWorkerCoordinator,
    LeaseBusy,
    LeaseLost,
    TaskNotClaimable,
)


T0 = "2026-09-17T16:00:00+00:00"
T30 = "2026-09-17T16:00:30+00:00"
T61 = "2026-09-17T16:01:01+00:00"
T90 = "2026-09-17T16:01:30+00:00"


class Patch009AutonomousWorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = CompanyDB(Path(self.tmp.name) / "company.db")
        self.workers = DurableWorkerCoordinator(self.db)
        self.task_id = self.db.create_task("durable worker acceptance test", "patch009")
        self.w1 = self.workers.register_worker(role="signal", worker_id="worker-a", now_iso=T0)
        self.w2 = self.workers.register_worker(role="signal", worker_id="worker-b", now_iso=T0)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_schema_10_is_applied(self):
        self.assertGreaterEqual(self.db.schema_version, 10)

    def test_unexpired_lease_has_single_owner(self):
        lease = self.workers.claim_task(self.task_id, worker_id=self.w1, ttl_seconds=60, now_iso=T0)
        with self.assertRaises(LeaseBusy):
            self.workers.claim_task(self.task_id, worker_id=self.w2, ttl_seconds=60, now_iso=T30)
        current = self.workers.get_lease(self.task_id)
        self.assertEqual(current.lease_token, lease.lease_token)
        self.assertEqual(current.worker_id, self.w1)
        self.assertEqual(current.generation, 1)

    def test_expired_lease_is_taken_over_as_new_generation(self):
        old = self.workers.claim_task(self.task_id, worker_id=self.w1, ttl_seconds=60, now_iso=T0)
        new = self.workers.claim_task(self.task_id, worker_id=self.w2, ttl_seconds=60, now_iso=T61)
        self.assertNotEqual(new.lease_token, old.lease_token)
        self.assertEqual(new.worker_id, self.w2)
        self.assertEqual(new.generation, 2)
        events = self.workers.list_lease_events(self.task_id)
        self.assertEqual([e["event_type"] for e in events], ["acquired", "expired_takeover"])
        self.assertEqual(events[-1]["prior_worker_id"], self.w1)
        self.assertEqual(events[-1]["prior_generation"], 1)

    def test_stale_worker_cannot_renew_or_release_after_takeover(self):
        old = self.workers.claim_task(self.task_id, worker_id=self.w1, ttl_seconds=60, now_iso=T0)
        self.workers.claim_task(self.task_id, worker_id=self.w2, ttl_seconds=60, now_iso=T61)
        with self.assertRaises(LeaseLost):
            self.workers.renew_lease(old, ttl_seconds=60, now_iso=T61)
        with self.assertRaises(LeaseLost):
            self.workers.release_lease(old, now_iso=T61)

    def test_renewal_requires_exact_current_lease(self):
        old = self.workers.claim_task(self.task_id, worker_id=self.w1, ttl_seconds=60, now_iso=T0)
        renewed = self.workers.renew_lease(old, ttl_seconds=60, now_iso=T30)
        self.assertEqual(renewed.lease_token, old.lease_token)
        self.assertEqual(renewed.generation, old.generation)
        self.assertEqual(renewed.heartbeat_at, T30)
        self.assertEqual(renewed.expires_at, T90)

    def test_release_then_reacquire_increments_generation(self):
        first = self.workers.claim_task(self.task_id, worker_id=self.w1, ttl_seconds=60, now_iso=T0)
        released = self.workers.release_lease(first, now_iso=T30)
        self.assertEqual(released.state, "released")
        second = self.workers.claim_task(self.task_id, worker_id=self.w2, ttl_seconds=60, now_iso=T30)
        self.assertEqual(second.generation, 2)
        self.assertNotEqual(second.lease_token, first.lease_token)
        events = self.workers.list_lease_events(self.task_id)
        self.assertEqual([e["event_type"] for e in events], ["acquired", "released", "acquired"])

    def test_lease_event_history_is_append_only(self):
        self.workers.claim_task(self.task_id, worker_id=self.w1, ttl_seconds=60, now_iso=T0)
        event = self.workers.list_lease_events(self.task_id)[0]
        conn = self.db._connection()
        with self.assertRaises(sqlite3.DatabaseError):
            conn.execute(
                "UPDATE task_worker_lease_events SET event_type='released' WHERE event_id=?",
                (event["event_id"],),
            )
        conn.rollback()
        with self.assertRaises(sqlite3.DatabaseError):
            conn.execute("DELETE FROM task_worker_lease_events WHERE event_id=?", (event["event_id"],))
        conn.rollback()

    def test_worker_lease_does_not_create_authority(self):
        before = self.db._connection().execute("SELECT COUNT(*) FROM temporal_warrants").fetchone()[0]
        self.workers.claim_task(self.task_id, worker_id=self.w1, ttl_seconds=60, now_iso=T0)
        after = self.db._connection().execute("SELECT COUNT(*) FROM temporal_warrants").fetchone()[0]
        self.assertEqual(before, 0)
        self.assertEqual(after, 0)
        self.assertEqual(self.db.list_action_requests(self.task_id), [])

    def test_completed_task_cannot_be_claimed(self):
        self.db.update_task(self.task_id, status="completed")
        with self.assertRaises(TaskNotClaimable):
            self.workers.claim_task(self.task_id, worker_id=self.w1, ttl_seconds=60, now_iso=T0)


if __name__ == "__main__":
    unittest.main()
