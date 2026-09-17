from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from .db import CompanyDB


CLAIMABLE_TASK_STATUSES = frozenset({"new", "running", "failed", "blocked"})


class WorkerLeaseError(RuntimeError):
    """Base class for durable worker lease failures."""


class WorkerNotActive(WorkerLeaseError):
    pass


class TaskNotClaimable(WorkerLeaseError):
    pass


class LeaseBusy(WorkerLeaseError):
    pass


class LeaseLost(WorkerLeaseError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_time(value: str | None) -> datetime:
    if value is None:
        return _utcnow()
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _canonical_json(value: dict[str, Any] | None) -> str:
    return json.dumps(value or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True)
class WorkerLease:
    task_id: str
    worker_id: str
    lease_token: str
    generation: int
    acquired_at: str
    heartbeat_at: str
    expires_at: str
    released_at: str | None
    state: str

    @classmethod
    def from_row(cls, row) -> "WorkerLease":
        return cls(
            task_id=str(row["task_id"]),
            worker_id=str(row["worker_id"]),
            lease_token=str(row["lease_token"]),
            generation=int(row["generation"]),
            acquired_at=str(row["acquired_at"]),
            heartbeat_at=str(row["heartbeat_at"]),
            expires_at=str(row["expires_at"]),
            released_at=row["released_at"],
            state=str(row["state"]),
        )


class DurableWorkerCoordinator:
    """Coordinates worker ownership without granting consequential authority.

    Worker leases answer only one question: which worker may advance this task
    right now? They do not satisfy, mint, extend, or replace StillPoint action
    warrants. Consequential external actions remain governed by the existing
    action/warrant gate.
    """

    def __init__(self, db: CompanyDB):
        self.db = db

    def register_worker(
        self,
        *,
        role: str,
        worker_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        now_iso: str | None = None,
    ) -> str:
        worker_id = worker_id or f"worker-{uuid.uuid4().hex[:16]}"
        now = _iso(_parse_time(now_iso))
        conn = self.db._connection()
        conn.execute(
            """INSERT INTO worker_instances
               (worker_id,role,started_at,last_heartbeat_at,status,metadata_json)
               VALUES(?,?,?,?,?,?)""",
            (worker_id, role, now, now, "active", _canonical_json(metadata)),
        )
        conn.commit()
        return worker_id

    def heartbeat_worker(self, worker_id: str, *, now_iso: str | None = None) -> dict[str, Any]:
        now = _iso(_parse_time(now_iso))
        conn = self.db._connection()
        cur = conn.execute(
            "UPDATE worker_instances SET last_heartbeat_at=? WHERE worker_id=? AND status='active'",
            (now, worker_id),
        )
        if cur.rowcount != 1:
            conn.rollback()
            raise WorkerNotActive(worker_id)
        conn.commit()
        row = conn.execute("SELECT * FROM worker_instances WHERE worker_id=?", (worker_id,)).fetchone()
        return dict(row)

    def stop_worker(self, worker_id: str, *, now_iso: str | None = None) -> None:
        now = _iso(_parse_time(now_iso))
        conn = self.db._connection()
        cur = conn.execute(
            "UPDATE worker_instances SET status='stopped',last_heartbeat_at=? WHERE worker_id=? AND status='active'",
            (now, worker_id),
        )
        if cur.rowcount != 1:
            conn.rollback()
            raise WorkerNotActive(worker_id)
        conn.commit()

    def _require_active_worker(self, conn, worker_id: str) -> None:
        row = conn.execute(
            "SELECT status FROM worker_instances WHERE worker_id=?", (worker_id,)
        ).fetchone()
        if not row or row["status"] != "active":
            raise WorkerNotActive(worker_id)

    def _require_claimable_task(self, conn, task_id: str) -> None:
        row = conn.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not row:
            raise KeyError(task_id)
        if row["status"] not in CLAIMABLE_TASK_STATUSES:
            raise TaskNotClaimable(f"task {task_id} status={row['status']}")

    def _record_event(
        self,
        conn,
        *,
        lease: WorkerLease,
        event_type: str,
        occurred_at: str,
        prior: WorkerLease | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        conn.execute(
            """INSERT INTO task_worker_lease_events
               (event_id,task_id,worker_id,lease_token,generation,event_type,occurred_at,
                prior_worker_id,prior_lease_token,prior_generation,metadata_json)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (
                uuid.uuid4().hex,
                lease.task_id,
                lease.worker_id,
                lease.lease_token,
                lease.generation,
                event_type,
                occurred_at,
                prior.worker_id if prior else None,
                prior.lease_token if prior else None,
                prior.generation if prior else None,
                _canonical_json(metadata),
            ),
        )

    def claim_task(
        self,
        task_id: str,
        *,
        worker_id: str,
        ttl_seconds: int = 60,
        now_iso: str | None = None,
    ) -> WorkerLease:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        now_dt = _parse_time(now_iso)
        now = _iso(now_dt)
        expires = _iso(now_dt + timedelta(seconds=ttl_seconds))
        conn = self.db._connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._require_active_worker(conn, worker_id)
            self._require_claimable_task(conn, task_id)
            row = conn.execute(
                "SELECT * FROM task_worker_leases WHERE task_id=?", (task_id,)
            ).fetchone()
            prior = WorkerLease.from_row(row) if row else None

            if prior and prior.state == "active" and _parse_time(prior.expires_at) > now_dt:
                if prior.worker_id == worker_id:
                    conn.commit()
                    return prior
                raise LeaseBusy(
                    f"task {task_id} is leased to {prior.worker_id} until {prior.expires_at}"
                )

            generation = (prior.generation + 1) if prior else 1
            token = uuid.uuid4().hex
            if prior:
                conn.execute(
                    """UPDATE task_worker_leases
                       SET worker_id=?,lease_token=?,generation=?,acquired_at=?,heartbeat_at=?,
                           expires_at=?,released_at=NULL,state='active'
                       WHERE task_id=?""",
                    (worker_id, token, generation, now, now, expires, task_id),
                )
            else:
                conn.execute(
                    """INSERT INTO task_worker_leases
                       (task_id,worker_id,lease_token,generation,acquired_at,heartbeat_at,
                        expires_at,released_at,state)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (task_id, worker_id, token, generation, now, now, expires, None, "active"),
                )

            lease = WorkerLease(
                task_id=task_id,
                worker_id=worker_id,
                lease_token=token,
                generation=generation,
                acquired_at=now,
                heartbeat_at=now,
                expires_at=expires,
                released_at=None,
                state="active",
            )
            event_type = (
                "expired_takeover"
                if prior and prior.state == "active" and _parse_time(prior.expires_at) <= now_dt
                else "acquired"
            )
            self._record_event(
                conn,
                lease=lease,
                event_type=event_type,
                occurred_at=now,
                prior=prior,
            )
            conn.commit()
            return lease
        except Exception:
            conn.rollback()
            raise

    def assert_lease(
        self,
        lease: WorkerLease,
        *,
        now_iso: str | None = None,
    ) -> WorkerLease:
        now_dt = _parse_time(now_iso)
        row = self.db._connection().execute(
            "SELECT * FROM task_worker_leases WHERE task_id=?", (lease.task_id,)
        ).fetchone()
        if not row:
            raise LeaseLost(lease.task_id)
        current = WorkerLease.from_row(row)
        if (
            current.state != "active"
            or current.worker_id != lease.worker_id
            or current.lease_token != lease.lease_token
            or current.generation != lease.generation
            or _parse_time(current.expires_at) <= now_dt
        ):
            raise LeaseLost(lease.task_id)
        return current

    def renew_lease(
        self,
        lease: WorkerLease,
        *,
        ttl_seconds: int = 60,
        now_iso: str | None = None,
    ) -> WorkerLease:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        now_dt = _parse_time(now_iso)
        now = _iso(now_dt)
        expires = _iso(now_dt + timedelta(seconds=ttl_seconds))
        conn = self.db._connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._require_active_worker(conn, lease.worker_id)
            current = self.assert_lease(lease, now_iso=now)
            cur = conn.execute(
                """UPDATE task_worker_leases
                   SET heartbeat_at=?,expires_at=?
                   WHERE task_id=? AND worker_id=? AND lease_token=? AND generation=? AND state='active'""",
                (now, expires, lease.task_id, lease.worker_id, lease.lease_token, lease.generation),
            )
            if cur.rowcount != 1:
                raise LeaseLost(lease.task_id)
            renewed = WorkerLease(
                task_id=current.task_id,
                worker_id=current.worker_id,
                lease_token=current.lease_token,
                generation=current.generation,
                acquired_at=current.acquired_at,
                heartbeat_at=now,
                expires_at=expires,
                released_at=None,
                state="active",
            )
            self._record_event(
                conn, lease=renewed, event_type="renewed", occurred_at=now, prior=current
            )
            conn.commit()
            return renewed
        except Exception:
            conn.rollback()
            raise

    def release_lease(
        self,
        lease: WorkerLease,
        *,
        now_iso: str | None = None,
    ) -> WorkerLease:
        now = _iso(_parse_time(now_iso))
        conn = self.db._connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            current = self.assert_lease(lease, now_iso=now)
            cur = conn.execute(
                """UPDATE task_worker_leases
                   SET state='released',released_at=?,heartbeat_at=?
                   WHERE task_id=? AND worker_id=? AND lease_token=? AND generation=? AND state='active'""",
                (now, now, lease.task_id, lease.worker_id, lease.lease_token, lease.generation),
            )
            if cur.rowcount != 1:
                raise LeaseLost(lease.task_id)
            released = WorkerLease(
                task_id=current.task_id,
                worker_id=current.worker_id,
                lease_token=current.lease_token,
                generation=current.generation,
                acquired_at=current.acquired_at,
                heartbeat_at=now,
                expires_at=current.expires_at,
                released_at=now,
                state="released",
            )
            self._record_event(
                conn, lease=released, event_type="released", occurred_at=now, prior=current
            )
            conn.commit()
            return released
        except Exception:
            conn.rollback()
            raise

    def get_lease(self, task_id: str) -> WorkerLease | None:
        row = self.db._connection().execute(
            "SELECT * FROM task_worker_leases WHERE task_id=?", (task_id,)
        ).fetchone()
        return WorkerLease.from_row(row) if row else None

    def list_lease_events(self, task_id: str) -> list[dict[str, Any]]:
        rows = self.db._connection().execute(
            """SELECT * FROM task_worker_lease_events
               WHERE task_id=? ORDER BY occurred_at,rowid""",
            (task_id,),
        ).fetchall()
        return [dict(row) for row in rows]
