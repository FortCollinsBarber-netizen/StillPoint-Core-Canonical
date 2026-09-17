"""Durable schedules and inbound-event triggers for StillPoint.

Triggers create internal tasks only. They do not create ActionRequests, approvals,
standing delegations, or temporal warrants. External authority remains a later
step inside the task's normal StillPoint execution path.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


def _parse_time(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception as exc:
        raise ValueError(f"invalid trigger timestamp: {value!r}") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("trigger timestamps must be timezone-aware")
    return dt.astimezone(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


@dataclass(frozen=True)
class InboundEvent:
    event_id: str
    source: str
    event_type: str
    dedupe_key: str
    occurred_at: str
    received_at: str
    payload: dict[str, Any]


class TriggerError(RuntimeError):
    pass


class TaskTriggerCoordinator:
    """Turns due schedules and durable inbound events into ordinary tasks."""

    def __init__(self, db):
        self.db = db

    def create_event_trigger(
        self,
        *,
        owner_role: str,
        source: str,
        event_type: str,
        goal_template: str,
        project: str | None,
        valid_from: str,
        review_by: str,
        trigger_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        if _parse_time(review_by) <= _parse_time(valid_from):
            raise ValueError("review_by must follow valid_from")
        trigger_id = trigger_id or f"trigger-{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc).isoformat()
        conn = self.db._connection()
        conn.execute(
            """INSERT INTO trigger_definitions
            (trigger_id,owner_role,trigger_kind,source,event_type,goal_template,project,status,
             valid_from,review_by,next_run_at,interval_seconds,max_runs,run_count,catch_up_policy,
             metadata_json,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                trigger_id,owner_role,"event",source,event_type,goal_template,project,"active",
                valid_from,review_by,None,None,None,0,"coalesce",_json(metadata or {}),now,now,
            ),
        )
        conn.commit()
        return trigger_id

    def create_interval_trigger(
        self,
        *,
        owner_role: str,
        goal_template: str,
        project: str | None,
        valid_from: str,
        review_by: str,
        next_run_at: str,
        interval_seconds: int,
        max_runs: int | None = None,
        trigger_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        if interval_seconds < 60:
            raise ValueError("interval_seconds must be at least 60")
        start = _parse_time(valid_from)
        review = _parse_time(review_by)
        next_run = _parse_time(next_run_at)
        if review <= start:
            raise ValueError("review_by must follow valid_from")
        if next_run < start or next_run >= review:
            raise ValueError("next_run_at must be inside trigger validity interval")
        if max_runs is not None and max_runs < 1:
            raise ValueError("max_runs must be positive")
        trigger_id = trigger_id or f"trigger-{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc).isoformat()
        conn = self.db._connection()
        conn.execute(
            """INSERT INTO trigger_definitions
            (trigger_id,owner_role,trigger_kind,source,event_type,goal_template,project,status,
             valid_from,review_by,next_run_at,interval_seconds,max_runs,run_count,catch_up_policy,
             metadata_json,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                trigger_id,owner_role,"schedule",None,None,goal_template,project,"active",
                valid_from,review_by,next_run_at,interval_seconds,max_runs,0,"coalesce",
                _json(metadata or {}),now,now,
            ),
        )
        conn.commit()
        return trigger_id

    def ingest_event(
        self,
        *,
        source: str,
        event_type: str,
        dedupe_key: str,
        occurred_at: str,
        received_at: str,
        payload: dict[str, Any],
    ) -> InboundEvent:
        if not source.strip() or not event_type.strip() or not dedupe_key.strip():
            raise ValueError("source, event_type, and dedupe_key required")
        _parse_time(occurred_at); _parse_time(received_at)
        event_id = "event-" + hashlib.sha256(
            f"{source}|{event_type}|{dedupe_key}".encode("utf-8")
        ).hexdigest()[:24]
        conn = self.db._connection()
        try:
            conn.execute(
                """INSERT INTO inbound_events
                (event_id,source,event_type,dedupe_key,occurred_at,received_at,payload_json)
                VALUES(?,?,?,?,?,?,?)""",
                (event_id,source,event_type,dedupe_key,occurred_at,received_at,_json(payload)),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            row = conn.execute("SELECT * FROM inbound_events WHERE dedupe_key=?", (dedupe_key,)).fetchone()
            if not row or row["source"] != source or row["event_type"] != event_type:
                raise
            event_id = row["event_id"]
        row = conn.execute("SELECT * FROM inbound_events WHERE event_id=?", (event_id,)).fetchone()
        return InboundEvent(
            event_id=row["event_id"],source=row["source"],event_type=row["event_type"],
            dedupe_key=row["dedupe_key"],occurred_at=row["occurred_at"],received_at=row["received_at"],
            payload=json.loads(row["payload_json"]),
        )

    def fire_event(self, event_id: str, *, now_iso: str) -> list[str]:
        now = _parse_time(now_iso)
        conn = self.db._connection()
        event = conn.execute("SELECT * FROM inbound_events WHERE event_id=?", (event_id,)).fetchone()
        if not event:
            raise KeyError(event_id)
        triggers = conn.execute(
            """SELECT * FROM trigger_definitions
               WHERE trigger_kind='event' AND status='active' AND source=? AND event_type=?
               ORDER BY created_at,trigger_id""",
            (event["source"], event["event_type"]),
        ).fetchall()
        task_ids=[]
        for trigger in triggers:
            if not self._trigger_current(trigger, now):
                continue
            task_id=self._fire(trigger,event=event,scheduled_for=None,now=now)
            if task_id:task_ids.append(task_id)
        return task_ids

    def fire_due(self, *, now_iso: str) -> list[str]:
        now = _parse_time(now_iso)
        conn = self.db._connection()
        triggers = conn.execute(
            """SELECT * FROM trigger_definitions
               WHERE trigger_kind='schedule' AND status='active' AND next_run_at IS NOT NULL
               ORDER BY next_run_at,trigger_id"""
        ).fetchall()
        task_ids=[]
        for trigger in triggers:
            if not self._trigger_current(trigger, now):
                continue
            scheduled=_parse_time(trigger["next_run_at"])
            if scheduled>now:continue
            if trigger["max_runs"] is not None and int(trigger["run_count"])>=int(trigger["max_runs"]):
                continue
            task_id=self._fire(trigger,event=None,scheduled_for=_iso(scheduled),now=now)
            if task_id:task_ids.append(task_id)
        return task_ids

    def context_for_task(self, task_id: str) -> dict[str, Any] | None:
        conn=self.db._connection()
        row=conn.execute(
            """SELECT f.*,t.owner_role,t.trigger_kind,t.source,t.event_type,e.payload_json,e.occurred_at
               FROM trigger_firings f
               JOIN trigger_definitions t ON t.trigger_id=f.trigger_id
               LEFT JOIN inbound_events e ON e.event_id=f.event_id
               WHERE f.task_id=?""",(task_id,)
        ).fetchone()
        if not row:return None
        out=dict(row)
        out["payload"]=json.loads(out.pop("payload_json")) if out.get("payload_json") else None
        return out

    @staticmethod
    def _trigger_current(trigger, now: datetime) -> bool:
        if trigger["status"]!="active":return False
        return _parse_time(trigger["valid_from"])<=now<_parse_time(trigger["review_by"])

    def _fire(self, trigger, *, event, scheduled_for: str | None, now: datetime) -> str | None:
        conn=self.db._connection(); now_iso=_iso(now)
        event_id=event["event_id"] if event else None
        slot=event_id or scheduled_for or ""
        idem=hashlib.sha256(f"{trigger['trigger_id']}|{slot}".encode()).hexdigest()
        task_id="task-"+idem[:20]
        goal=trigger["goal_template"].replace("{trigger_id}",trigger["trigger_id"])
        if event:
            goal=goal.replace("{event_id}",event_id).replace("{source}",event["source"]).replace("{event_type}",event["event_type"])
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing=conn.execute("SELECT task_id FROM trigger_firings WHERE idempotency_key=?",(idem,)).fetchone()
            if existing:
                conn.rollback();return None
            conn.execute(
                "INSERT INTO tasks(id,created_at,updated_at,goal,project,status) VALUES(?,?,?,?,?,?)",
                (task_id,now_iso,now_iso,goal,trigger["project"],"new"),
            )
            firing_id="firing-"+uuid.uuid4().hex[:20]
            conn.execute(
                """INSERT INTO trigger_firings
                (firing_id,trigger_id,event_id,scheduled_for,task_id,idempotency_key,fired_at)
                VALUES(?,?,?,?,?,?,?)""",
                (firing_id,trigger["trigger_id"],event_id,scheduled_for,task_id,idem,now_iso),
            )
            if trigger["trigger_kind"]=="schedule":
                interval=int(trigger["interval_seconds"])
                next_dt=_parse_time(trigger["next_run_at"])
                while next_dt<=now:next_dt+=timedelta(seconds=interval)
                new_count=int(trigger["run_count"])+1
                new_status="active"
                if trigger["max_runs"] is not None and new_count>=int(trigger["max_runs"]):new_status="stopped"
                conn.execute(
                    """UPDATE trigger_definitions
                       SET run_count=?,next_run_at=?,status=?,updated_at=? WHERE trigger_id=?""",
                    (new_count,_iso(next_dt),new_status,now_iso,trigger["trigger_id"]),
                )
            else:
                conn.execute(
                    "UPDATE trigger_definitions SET run_count=run_count+1,updated_at=? WHERE trigger_id=?",
                    (now_iso,trigger["trigger_id"]),
                )
            conn.commit();return task_id
        except Exception:
            conn.rollback();raise
