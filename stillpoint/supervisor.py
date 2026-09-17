"""StillPoint 0.4 autonomous company supervisor.

The supervisor owns continuity, not specialist jurisdiction. It fires durable
schedules, maintains persistent office workers, repairs impossible exhausted-task
state, and reconstructs operation after restart. Worker leases remain task
ownership only and never substitute for external-action authority.
"""
from __future__ import annotations

import fcntl
import json
import os
import socket
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .db import CompanyDB
from .providers import make_provider
from .registry import AgentRegistry
from .runtime import CompanyRuntime
from .triggers import TaskTriggerCoordinator
from .workers import DurableWorkerCoordinator, WorkerNotActive
from .worker_service import PersistentWorkerService, WorkerServiceConfig

OFFICE_ROLES = (
    "orchestra",
    "author",
    "press",
    "signal",
    "ledger",
    "research",
    "builder",
    "stillpoint",
)

MAIL_TRIGGER_SOURCES = ("icloud", "gmail")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _now()).astimezone(timezone.utc).isoformat()


@dataclass(frozen=True)
class SupervisorConfig:
    root: Path
    provider_name: str = "mock"
    default_model: str = "default"
    supervisor_interval_seconds: float = 2.0
    worker_poll_seconds: float = 1.0
    lease_ttl_seconds: int = 90
    heartbeat_interval_seconds: int = 20
    retry_backoff_seconds: int = 60
    max_failures: int = 3
    start_office_workers: bool = True
    office_restart_backoff_seconds: float = 10.0

    def __post_init__(self):
        root=Path(self.root).expanduser().resolve()
        object.__setattr__(self,"root",root)
        if self.supervisor_interval_seconds <= 0 or self.worker_poll_seconds <= 0:
            raise ValueError("supervisor intervals must be positive")
        if self.heartbeat_interval_seconds >= self.lease_ttl_seconds:
            raise ValueError("heartbeat must be shorter than lease ttl")
        if self.max_failures < 1:
            raise ValueError("max_failures must be positive")
        if self.office_restart_backoff_seconds < 0:
            raise ValueError("office restart backoff cannot be negative")


def _runtime(config: SupervisorConfig) -> CompanyRuntime:
    provider=make_provider(config.provider_name)
    config_path=config.root/"config"/"agents.json"
    if not config_path.is_file():
        config_path=Path(__file__).resolve().parent/"defaults"/"agents.json"
    return CompanyRuntime(
        root=config.root,
        db=CompanyDB(config.root/"state"/"company.sqlite"),
        registry=AgentRegistry(config_path),
        provider=provider,
        default_model=config.default_model,
        smart_routing=os.getenv("STILLPOINT_SMART_ROUTING","1")=="1",
        allowed_import_roots=[config.root],
    )


class OfficeWorker(threading.Thread):
    def __init__(self, *, role: str, config: SupervisorConfig, stop_event: threading.Event):
        super().__init__(name=f"stillpoint-office-{role}", daemon=True)
        if role not in OFFICE_ROLES:
            raise ValueError(role)
        self.role=role
        self.config=config
        self.stop_event=stop_event
        self.worker_id=""
        self.last_error=""
        self.started_at=""
        self.completed_attempts=0

    def run(self):
        rt=None
        coord=None
        try:
            rt=_runtime(self.config)
            coord=DurableWorkerCoordinator(rt.db)
            self.worker_id=f"office:{self.role}:{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"
            self.started_at=_iso()
            coord.register_worker(
                role=self.role,
                worker_id=self.worker_id,
                metadata={
                    "service":"stillpointd",
                    "office":self.role,
                    "host":socket.gethostname(),
                    "pid":os.getpid(),
                },
            )
            db_path=self.config.root/"state"/"company.sqlite"

            def coordinator_factory():
                return DurableWorkerCoordinator(CompanyDB(db_path))

            service=PersistentWorkerService(
                db=rt.db,
                coordinator=coord,
                coordinator_factory=coordinator_factory,
                config=WorkerServiceConfig(
                    role=self.role,
                    lease_ttl_seconds=self.config.lease_ttl_seconds,
                    heartbeat_interval_seconds=self.config.heartbeat_interval_seconds,
                    retry_backoff_seconds=self.config.retry_backoff_seconds,
                    max_failures=self.config.max_failures,
                    auto_retry_failed=True,
                    triggered_only=(self.role!="orchestra"),
                    excluded_trigger_sources=MAIL_TRIGGER_SOURCES if self.role=="signal" else (),
                ),
                worker_id=self.worker_id,
            )

            def execute(task_id, guard):
                result=rt.resume(task_id)
                self.completed_attempts += 1
                return {
                    "task_id":result.task_id,
                    "status":result.status.value,
                    "primary":result.plan.primary,
                }

            service.serve(
                execute,
                poll_interval_seconds=self.config.worker_poll_seconds,
                stop_event=self.stop_event,
            )
        except Exception as exc:
            self.last_error=f"{type(exc).__name__}: {exc}"
        finally:
            if coord is not None and self.worker_id:
                try:
                    coord.stop_worker(self.worker_id)
                except WorkerNotActive:
                    pass
                except Exception:
                    pass
            if rt is not None:
                try:
                    rt.db.close()
                except Exception:
                    pass


class CompanySupervisor:
    def __init__(self, config: SupervisorConfig):
        self.config=config
        self.config.root.mkdir(parents=True,exist_ok=True)
        (self.config.root/"state").mkdir(parents=True,exist_ok=True)
        self.db=CompanyDB(self.config.root/"state"/"company.sqlite")
        if self.db.schema_version < 19:
            raise RuntimeError(f"StillPoint 0.4 requires schema >=19, found {self.db.schema_version}")
        self.triggers=TaskTriggerCoordinator(self.db)
        self.stop_event=threading.Event()
        self.office_workers:list[OfficeWorker]=[]
        self._office_last_started:dict[str,float]={}
        self._lock_handle=None
        self._last_fired:list[str]=[]
        self._repair_count=0

    @property
    def status_path(self) -> Path:
        return self.config.root/"state"/"stillpointd_status.json"

    def acquire_singleton(self):
        path=self.config.root/"state"/"stillpointd.lock"
        handle=open(path,"a+")
        try:
            fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:
            handle.close()
            raise RuntimeError("another stillpointd supervisor already owns this runtime") from exc
        self._lock_handle=handle

    def repair_exhausted_task_states(self, *, now_iso: str | None=None) -> int:
        now_iso=now_iso or _iso()
        conn=self.db._connection()
        cols={row["name"] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
        assignments=["status='failed'"]
        args=[]
        if "updated_at" in cols:
            assignments.append("updated_at=?");args.append(now_iso)
        if "error" in cols:
            assignments.append(
                "error=CASE WHEN error IS NULL OR trim(error)='' "
                "THEN 'worker retry exhausted; state repaired by stillpointd' ELSE error END"
            )
        sql=(
            f"UPDATE tasks SET {','.join(assignments)} "
            "WHERE status IN ('new','running') AND id IN "
            "(SELECT task_id FROM worker_task_retry_state WHERE exhausted=1)"
        )
        cur=conn.execute(sql,args)
        conn.commit()
        self._repair_count += int(cur.rowcount or 0)
        return int(cur.rowcount or 0)

    def retire_prior_supervisor_workers(self, *, now_iso: str | None=None) -> int:
        now_iso=now_iso or _iso()
        conn=self.db._connection()
        rows=conn.execute(
            "SELECT worker_id,metadata_json FROM worker_instances WHERE status='active'"
        ).fetchall()
        ids=[]
        for row in rows:
            try:
                metadata=json.loads(row["metadata_json"] or "{}")
            except Exception:
                metadata={}
            if metadata.get("service")=="stillpointd":
                ids.append(row["worker_id"])

        coordinator=DurableWorkerCoordinator(self.db)
        for worker_id in ids:
            lease_rows=conn.execute(
                "SELECT task_id FROM task_worker_leases "
                "WHERE worker_id=? AND state='active'",
                (worker_id,),
            ).fetchall()
            for lease_row in lease_rows:
                lease=coordinator.get_lease(lease_row["task_id"])
                if lease is None:
                    continue
                try:
                    coordinator.release_lease(lease,now_iso=now_iso)
                except Exception:
                    pass
            conn.execute(
                "UPDATE worker_instances SET status='stopped',last_heartbeat_at=? "
                "WHERE worker_id=? AND status='active'",
                (now_iso,worker_id),
            )
        conn.commit()
        return len(ids)

    def ensure_offices(self):
        if not self.config.start_office_workers:
            return
        # Keep only live thread objects. Durable worker history remains in SQLite;
        # the in-memory supervisor list should represent current process topology.
        self.office_workers=[w for w in self.office_workers if w.is_alive()]
        now_mono=time.monotonic()
        alive={w.role for w in self.office_workers}
        for role in OFFICE_ROLES:
            if role in alive:
                continue
            last=self._office_last_started.get(role)
            if last is not None and now_mono-last < self.config.office_restart_backoff_seconds:
                continue
            worker=OfficeWorker(role=role,config=self.config,stop_event=self.stop_event)
            self._office_last_started[role]=now_mono
            worker.start()
            self.office_workers.append(worker)

    def start_offices(self):
        self.ensure_offices()

    def tick(self, *, now_iso: str | None=None) -> dict[str,Any]:
        now_iso=now_iso or _iso()
        repaired=self.repair_exhausted_task_states(now_iso=now_iso)
        self.ensure_offices()
        fired=self.triggers.fire_due(now_iso=now_iso)
        self._last_fired=list(fired)
        snapshot=self.snapshot(now_iso=now_iso)
        snapshot["repaired_exhausted_task_states_this_tick"]=repaired
        snapshot["scheduled_tasks_fired_this_tick"]=list(fired)
        self.write_snapshot(snapshot)
        return snapshot

    def snapshot(self, *, now_iso: str | None=None) -> dict[str,Any]:
        now_iso=now_iso or _iso()
        conn=self.db._connection()
        status_counts={
            row["status"]:row["count"]
            for row in conn.execute(
                "SELECT status,COUNT(*) AS count FROM tasks GROUP BY status ORDER BY status"
            ).fetchall()
        }
        exhausted=conn.execute(
            "SELECT COUNT(*) AS n FROM worker_task_retry_state WHERE exhausted=1"
        ).fetchone()["n"]
        active_triggers=conn.execute(
            "SELECT COUNT(*) AS n FROM trigger_definitions WHERE status='active'"
        ).fetchone()["n"]
        workers=[]
        for row in conn.execute(
            "SELECT worker_id,role,last_heartbeat_at,status,metadata_json "
            "FROM worker_instances ORDER BY role,worker_id"
        ).fetchall():
            item=dict(row)
            try:item["metadata"]=json.loads(item.pop("metadata_json") or "{}")
            except Exception:item["metadata"]={}
            workers.append(item)
        office_threads={
            w.role:{
                "thread_alive":w.is_alive(),
                "worker_id":w.worker_id,
                "last_error":w.last_error,
                "completed_attempts":w.completed_attempts,
            }
            for w in self.office_workers
        }
        return {
            "kind":"stillpointd_status_cache",
            "authoritative":False,
            "observed_at":now_iso,
            "schema_version":self.db.schema_version,
            "offices":list(OFFICE_ROLES),
            "office_threads":office_threads,
            "task_status_counts":status_counts,
            "active_triggers":active_triggers,
            "exhausted_retry_rows":exhausted,
            "repair_count_since_start":self._repair_count,
            "worker_instances":workers,
        }

    def write_snapshot(self, snapshot: dict[str,Any]):
        path=self.status_path
        tmp=path.with_suffix(".tmp")
        tmp.write_text(json.dumps(snapshot,indent=2,ensure_ascii=False,default=str)+"\n")
        os.replace(tmp,path)

    def serve(self):
        self.acquire_singleton()
        self.retire_prior_supervisor_workers()
        self.repair_exhausted_task_states()
        self.start_offices()
        try:
            while not self.stop_event.is_set():
                self.tick()
                self.stop_event.wait(self.config.supervisor_interval_seconds)
        finally:
            self.stop_event.set()
            for worker in self.office_workers:
                worker.join(timeout=max(2.0,self.config.heartbeat_interval_seconds+1))
            try:
                self.write_snapshot(self.snapshot())
            except Exception:
                pass
            self.close()

    def close(self):
        try:self.db.close()
        except Exception:pass
        if self._lock_handle is not None:
            try:fcntl.flock(self._lock_handle.fileno(),fcntl.LOCK_UN)
            except Exception:pass
            try:self._lock_handle.close()
            except Exception:pass
            self._lock_handle=None
