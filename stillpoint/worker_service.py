"""Persistent bounded worker service for StillPoint Autonomous Operations.

The service may own and advance internal tasks. It never mints or substitutes for
external-action authority. Executors must still cross the ordinary StillPoint
warrant boundary for consequential actions.
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from .workers import DurableWorkerCoordinator, LeaseBusy, LeaseLost, WorkerLease


def _now() -> datetime: return datetime.now(timezone.utc)
def _parse(value: str) -> datetime:
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    if dt.tzinfo is None or dt.utcoffset() is None: raise ValueError('timezone-aware timestamp required')
    return dt.astimezone(timezone.utc)
def _iso(dt: datetime) -> str: return dt.astimezone(timezone.utc).isoformat()
def _json(v: Any) -> str: return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str)

@dataclass(frozen=True)
class WorkerServiceConfig:
    role: str
    lease_ttl_seconds: int = 90
    heartbeat_interval_seconds: int = 20
    retry_backoff_seconds: int = 300
    max_failures: int = 3
    auto_retry_failed: bool = False
    triggered_only: bool = True
    excluded_trigger_sources: tuple[str, ...] = ()
    use_office_assignments: bool = False

    def __post_init__(self):
        if not self.role.strip(): raise ValueError('role required')
        if self.lease_ttl_seconds < 10: raise ValueError('lease ttl too short')
        if self.heartbeat_interval_seconds < 1 or self.heartbeat_interval_seconds >= self.lease_ttl_seconds:
            raise ValueError('heartbeat interval must be positive and shorter than lease ttl')
        if self.retry_backoff_seconds < 0 or self.max_failures < 1: raise ValueError('invalid retry policy')

class LeaseHeartbeatGuard:
    """Renews a lease from a separate DB/coordinator while work is blocking."""
    def __init__(self, *, coordinator_factory: Callable[[], DurableWorkerCoordinator], lease: WorkerLease,
                 ttl_seconds: int, interval_seconds: int):
        self._factory=coordinator_factory; self.lease=lease; self.ttl=ttl_seconds; self.interval=interval_seconds
        self._stop=threading.Event(); self._lost=threading.Event(); self._error: Exception|None=None; self._thread=None

    def heartbeat_once(self, now_iso: str|None=None) -> WorkerLease:
        coord=self._factory()
        try:
            coord.heartbeat_worker(self.lease.worker_id, now_iso=now_iso)
            self.lease=coord.renew_lease(self.lease, ttl_seconds=self.ttl, now_iso=now_iso)
            return self.lease
        except Exception as exc:
            self._error=exc; self._lost.set(); raise
        finally:
            db=getattr(coord,'db',None)
            if db is not None and hasattr(db,'close'):
                try: db.close()
                except Exception: pass

    def _run(self):
        while not self._stop.wait(self.interval):
            try: self.heartbeat_once()
            except Exception: return

    def start(self):
        if self._thread is not None: return
        self._thread=threading.Thread(target=self._run,name=f'stillpoint-lease-{self.lease.task_id}',daemon=True); self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread: self._thread.join(timeout=max(1,self.interval+1))

    def assert_current(self, *, now_iso: str|None=None) -> WorkerLease:
        if self._lost.is_set(): raise LeaseLost(str(self._error or self.lease.task_id))
        coord=self._factory()
        try: return coord.assert_lease(self.lease,now_iso=now_iso)
        finally:
            db=getattr(coord,'db',None)
            if db is not None and hasattr(db,'close'):
                try: db.close()
                except Exception: pass

class PersistentWorkerService:
    def __init__(self, *, db, coordinator: DurableWorkerCoordinator, coordinator_factory: Callable[[], DurableWorkerCoordinator],
                 config: WorkerServiceConfig, worker_id: str):
        self.db=db; self.coordinator=coordinator; self.coordinator_factory=coordinator_factory; self.config=config; self.worker_id=worker_id

    def _event(self, lease: WorkerLease, attempt_id: str, event_type: str, *, now_iso: str, error: str='', retry_after: str|None=None, metadata=None):
        self.db._connection().execute(
            """INSERT INTO worker_task_execution_events(event_id,attempt_id,task_id,worker_id,lease_token,generation,role,event_type,occurred_at,retry_after,error,metadata_json)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (uuid.uuid4().hex,attempt_id,lease.task_id,lease.worker_id,lease.lease_token,lease.generation,self.config.role,event_type,now_iso,retry_after,error,_json(metadata or {})))
        self.db._connection().commit()

    def _retry_row(self, task_id: str):
        return self.db._connection().execute('SELECT * FROM worker_task_retry_state WHERE task_id=?',(task_id,)).fetchone()

    def _eligible(self, task_id: str, status: str, now: datetime) -> bool:
        # Retry evidence outranks stale task status. A task cannot become eligible
        # merely because its tasks.status still says new/running after execution failed.
        row=self._retry_row(task_id)
        if row:
            if int(row['exhausted']): return False
            if row['last_outcome']=='failed':
                if not self.config.auto_retry_failed: return False
                if row['next_eligible_at'] and _parse(row['next_eligible_at']) > now:
                    return False
        if status in {'new','running'}: return True
        if status!='failed' or not self.config.auto_retry_failed: return False
        if not row or row['last_outcome']!='failed': return False
        return not row['next_eligible_at'] or _parse(row['next_eligible_at']) <= now

    def eligible_task_ids(self, *, now_iso: str, limit: int=20) -> list[str]:
        now=_parse(now_iso); conn=self.db._connection()
        rows=conn.execute("SELECT id,status FROM tasks WHERE status IN ('new','running','failed','blocked') ORDER BY created_at,id LIMIT ?",(max(limit*5,limit),)).fetchall()
        out=[]
        for row in rows:
            if not self._eligible(row['id'],row['status'],now): continue
            firing=conn.execute("""SELECT d.* FROM trigger_firings f JOIN trigger_definitions d ON d.trigger_id=f.trigger_id WHERE f.task_id=?""",(row['id'],)).fetchone()
            assignment=None
            if self.config.use_office_assignments:
                has_table=conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='task_office_assignments'").fetchone()
                if has_table:
                    assignment=conn.execute(
                        "SELECT * FROM task_office_assignments WHERE task_id=? AND state='active'",
                        (row['id'],),
                    ).fetchone()
                # In office-runtime mode, durable assignment is the ownership gate.
                # Do not let Orchestra (triggered_only=False) race the supervisor and
                # claim a newly queued task before assign_new_unowned_to_orchestra()
                # has created the accountable owner record.
                if assignment is None or assignment['owner_role']!=self.config.role:
                    continue
            if firing:
                if firing['owner_role']!=self.config.role: continue
                keys=set(firing.keys()); source=firing['source'] if 'source' in keys else None
                if source and source in self.config.excluded_trigger_sources: continue
            elif not self.config.use_office_assignments and self.config.triggered_only:
                continue
            out.append(row['id'])
            if len(out)>=limit: break
        return out

    def claim_next(self, *, now_iso: str) -> WorkerLease|None:
        for task_id in self.eligible_task_ids(now_iso=now_iso):
            try: return self.coordinator.claim_task(task_id,worker_id=self.worker_id,ttl_seconds=self.config.lease_ttl_seconds,now_iso=now_iso)
            except LeaseBusy: continue
        return None

    def _set_retry(self, task_id: str, *, outcome: str, now: datetime, error: str='') -> str|None:
        row=self._retry_row(task_id); failures=int(row['failure_count']) if row else 0
        if outcome=='failed': failures += 1
        elif outcome=='succeeded': failures=0
        exhausted=1 if outcome=='failed' and failures>=self.config.max_failures else 0
        retry_after=None
        if outcome=='failed' and self.config.auto_retry_failed and not exhausted:
            retry_after=_iso(now+timedelta(seconds=self.config.retry_backoff_seconds))
        self.db._connection().execute(
            """INSERT INTO worker_task_retry_state(task_id,failure_count,next_eligible_at,last_outcome,exhausted,updated_at)
               VALUES(?,?,?,?,?,?) ON CONFLICT(task_id) DO UPDATE SET failure_count=excluded.failure_count,next_eligible_at=excluded.next_eligible_at,last_outcome=excluded.last_outcome,exhausted=excluded.exhausted,updated_at=excluded.updated_at""",
            (task_id,failures,retry_after,outcome,exhausted,_iso(now)))
        self.db._connection().commit(); return retry_after

    def _mark_task_failed(self, task_id: str, *, error: str, now_iso: str) -> None:
        updater=getattr(self.db,'update_task',None)
        if callable(updater):
            updater(task_id,status='failed',error=error)
            return
        conn=self.db._connection()
        cols={str(row[1]) for row in conn.execute('PRAGMA table_info(tasks)').fetchall()}
        assignments=["status='failed'"]; args=[]
        if 'error' in cols:
            assignments.append('error=?'); args.append(error)
        if 'updated_at' in cols:
            assignments.append('updated_at=?'); args.append(now_iso)
        args.append(task_id)
        conn.execute(f"UPDATE tasks SET {','.join(assignments)} WHERE id=?",args)
        conn.commit()

    def run_once(self, executor: Callable[[str,LeaseHeartbeatGuard],Any], *, now_iso: str|None=None) -> dict[str,Any]|None:
        start=_parse(now_iso) if now_iso else _now(); logical_now=_iso(start) if now_iso is not None else None; lease=self.claim_next(now_iso=_iso(start))
        if not lease: return None
        attempt_id='attempt-'+uuid.uuid4().hex[:20]; self._event(lease,attempt_id,'started',now_iso=_iso(start))
        guard=LeaseHeartbeatGuard(coordinator_factory=self.coordinator_factory,lease=lease,ttl_seconds=self.config.lease_ttl_seconds,interval_seconds=self.config.heartbeat_interval_seconds)
        guard.start(); outcome='succeeded'; error=''; retry_after=None
        try:
            result=executor(lease.task_id,guard)
            guard.assert_current(now_iso=logical_now)
            task=self.db.get_task(lease.task_id) or {}
            if task.get('status')=='blocked': outcome='blocked'
            elif task.get('status')=='failed': outcome='failed'
            event_now=start if logical_now is not None else _now()
            retry_after=self._set_retry(lease.task_id,outcome=outcome,now=event_now)
            self._event(guard.lease,attempt_id,outcome,now_iso=_iso(event_now),retry_after=retry_after)
            return {'task_id':lease.task_id,'attempt_id':attempt_id,'outcome':outcome,'result':result}
        except LeaseLost as exc:
            outcome='lease_lost'; error=str(exc); event_now=start if logical_now is not None else _now(); self._set_retry(lease.task_id,outcome=outcome,now=event_now)
            self._event(guard.lease,attempt_id,'lease_lost',now_iso=_iso(event_now),error=error)
            raise
        except Exception as exc:
            outcome='failed'; error=f'{type(exc).__name__}: {exc}'; event_now=start if logical_now is not None else _now()
            retry_after=self._set_retry(lease.task_id,outcome=outcome,now=event_now,error=error)
            event_error=error
            try:
                self._mark_task_failed(lease.task_id,error=error,now_iso=_iso(event_now))
            except Exception as mark_exc:
                event_error += f"; task_status_update_failed={type(mark_exc).__name__}: {mark_exc}"
            self._event(guard.lease,attempt_id,'failed',now_iso=_iso(event_now),error=event_error,retry_after=retry_after)
            raise
        finally:
            guard.stop()
            try: self.coordinator.release_lease(guard.lease,now_iso=logical_now)
            except LeaseLost: pass

    def serve(self, executor, *, poll_interval_seconds: float=2.0, stop_event: threading.Event|None=None):
        stop_event=stop_event or threading.Event()
        while not stop_event.is_set():
            self.coordinator.heartbeat_worker(self.worker_id)
            try:
                result=self.run_once(executor)
            except Exception:
                # A task failure is durable task state, not a reason to kill the worker daemon.
                # KeyboardInterrupt/SystemExit still propagate because they are BaseException.
                stop_event.wait(poll_interval_seconds)
                continue
            if result is None: stop_event.wait(poll_interval_seconds)
