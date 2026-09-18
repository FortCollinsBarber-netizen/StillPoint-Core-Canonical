"""Durable office accountability for StillPoint 0.4.

Assignments answer which office is accountable for a task. Worker leases answer
which worker may advance it right now. Neither grants external-action authority.
"""
from __future__ import annotations
import json, uuid
from datetime import datetime, timezone
from typing import Any

OFFICE_ROLES=("orchestra","author","press","signal","ledger","research","builder","stillpoint")
MAX_HANDOFFS=8

def _now(): return datetime.now(timezone.utc).isoformat()
def _json(v): return json.dumps(v or {},sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str)

class OfficeAssignmentConflict(RuntimeError): pass
class OfficeHandoffLimit(RuntimeError): pass

class OfficeRuntimeCoordinator:
    def __init__(self,db): self.db=db
    def initialize_offices(self,*,now_iso=None,conn=None,commit=True):
        now_iso=now_iso or _now(); c=conn or self.db._connection()
        for role in OFFICE_ROLES:
            c.execute("""INSERT INTO office_runtime_state
              (role,desired_state,health_state,current_worker_id,generation,restart_count,last_started_at,last_heartbeat_at,last_completed_at,last_error,updated_at)
              VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(role) DO NOTHING""",
              (role,"active","starting",None,0,0,None,None,None,None,now_iso))
        if commit: c.commit()
    def _event(self,*,role,worker_id,event_type,occurred_at,error="",metadata=None,conn=None):
        c=conn or self.db._connection()
        c.execute("""INSERT INTO office_runtime_events
          (event_id,role,worker_id,event_type,occurred_at,error,metadata_json) VALUES(?,?,?,?,?,?,?)""",
          (uuid.uuid4().hex,role,worker_id,event_type,occurred_at,error,_json(metadata)))
    def worker_started(self,role,worker_id,*,now_iso=None):
        if role not in OFFICE_ROLES: raise ValueError(role)
        now_iso=now_iso or _now(); c=self.db._connection()
        try:
            c.execute("BEGIN IMMEDIATE")
            row=c.execute("SELECT * FROM office_runtime_state WHERE role=?",(role,)).fetchone()
            if not row:
                self.initialize_offices(now_iso=now_iso,conn=c,commit=False)
                row=c.execute("SELECT * FROM office_runtime_state WHERE role=?",(role,)).fetchone()
            generation=int(row['generation'])+1; restarts=int(row['restart_count'])+(1 if int(row['generation'])>0 else 0)
            et='restarted' if int(row['generation'])>0 else 'started'
            c.execute("""UPDATE office_runtime_state SET desired_state='active',health_state='healthy',current_worker_id=?,generation=?,restart_count=?,last_started_at=?,last_heartbeat_at=?,last_error=NULL,updated_at=? WHERE role=?""",
                      (worker_id,generation,restarts,now_iso,now_iso,now_iso,role))
            self._event(role=role,worker_id=worker_id,event_type=et,occurred_at=now_iso,conn=c)
            c.commit()
        except Exception:
            c.rollback(); raise
    def observe_health(self,role,*,worker_id,heartbeat_at,healthy,error="",now_iso=None):
        now_iso=now_iso or _now(); c=self.db._connection()
        try:
            c.execute("BEGIN IMMEDIATE")
            row=c.execute("SELECT * FROM office_runtime_state WHERE role=?",(role,)).fetchone()
            if not row:
                self.initialize_offices(now_iso=now_iso,conn=c,commit=False)
                row=c.execute("SELECT * FROM office_runtime_state WHERE role=?",(role,)).fetchone()
            new='healthy' if healthy else 'degraded'; old=row['health_state']
            c.execute("UPDATE office_runtime_state SET health_state=?,current_worker_id=?,last_heartbeat_at=?,last_error=?,updated_at=? WHERE role=?",
                      (new,worker_id,heartbeat_at,error or None,now_iso,role))
            if old!=new: self._event(role=role,worker_id=worker_id,event_type=new,occurred_at=now_iso,error=error,conn=c)
            c.commit()
        except Exception:
            c.rollback(); raise
    def worker_stopped(self,role,worker_id,*,error="",now_iso=None):
        now_iso=now_iso or _now(); c=self.db._connection()
        try:
            c.execute("BEGIN IMMEDIATE")
            c.execute("""UPDATE office_runtime_state
                         SET health_state='stopped',current_worker_id=NULL,last_error=?,updated_at=?
                         WHERE role=? AND (current_worker_id=? OR current_worker_id IS NULL)""",
                      (error or None,now_iso,role,worker_id))
            self._event(role=role,worker_id=worker_id,event_type='stopped',occurred_at=now_iso,error=error,conn=c)
            c.commit()
        except Exception:
            c.rollback(); raise
    def mark_completed(self,role,worker_id,*,now_iso=None):
        now_iso=now_iso or _now(); self.db._connection().execute("UPDATE office_runtime_state SET last_completed_at=?,updated_at=? WHERE role=? AND current_worker_id=?",(now_iso,now_iso,role,worker_id)); self.db._connection().commit()
    def get_office_states(self): return [dict(r) for r in self.db._connection().execute("SELECT * FROM office_runtime_state ORDER BY role").fetchall()]
    def get_assignment(self,task_id):
        r=self.db._connection().execute("SELECT * FROM task_office_assignments WHERE task_id=?",(task_id,)).fetchone(); return dict(r) if r else None
    def list_assignments(self,*,state=None):
        c=self.db._connection(); rows=c.execute("SELECT * FROM task_office_assignments WHERE state=? ORDER BY updated_at,task_id",(state,)).fetchall() if state else c.execute("SELECT * FROM task_office_assignments ORDER BY updated_at,task_id").fetchall(); return [dict(r) for r in rows]
    def list_handoffs(self,task_id): return [dict(r) for r in self.db._connection().execute("SELECT * FROM task_office_handoff_events WHERE task_id=? ORDER BY occurred_at,rowid",(task_id,)).fetchall()]
    def _handoff_event(self,*,task_id,from_role,to_role,event_type,reason,occurred_at,metadata=None,conn=None):
        c=conn or self.db._connection()
        c.execute("""INSERT INTO task_office_handoff_events(event_id,task_id,from_role,to_role,event_type,reason,occurred_at,metadata_json) VALUES(?,?,?,?,?,?,?,?)""",
          (uuid.uuid4().hex,task_id,from_role,to_role,event_type,reason,occurred_at,_json(metadata)))
    def assign_task(self,task_id,owner_role,*,assigned_by,reason,now_iso=None,event_type='assigned'):
        if owner_role not in OFFICE_ROLES: raise ValueError(owner_role)
        if not assigned_by.strip() or not reason.strip(): raise ValueError('assignment evidence required')
        now_iso=now_iso or _now(); c=self.db._connection()
        try:
            c.execute("BEGIN IMMEDIATE")
            cur=c.execute("SELECT * FROM task_office_assignments WHERE task_id=?",(task_id,)).fetchone()
            if cur:
                if cur['owner_role']==owner_role and cur['state']=='active':
                    c.rollback(); return dict(cur)
                raise OfficeAssignmentConflict(f"task {task_id} already assigned to {cur['owner_role']} state={cur['state']}; explicit handoff required")
            c.execute("""INSERT INTO task_office_assignments(task_id,owner_role,assigned_at,assigned_by,reason,handoff_count,state,updated_at) VALUES(?,?,?,?,?,?,?,?)""",
                      (task_id,owner_role,now_iso,assigned_by,reason,0,'active',now_iso))
            self._handoff_event(task_id=task_id,from_role=None,to_role=owner_role,event_type=event_type,reason=reason,occurred_at=now_iso,metadata={'assigned_by':assigned_by},conn=c)
            c.commit()
        except Exception:
            c.rollback(); raise
        return self.get_assignment(task_id)
    def handoff_task(self,task_id,*,from_role,to_role,reason,now_iso=None):
        if from_role==to_role: raise ValueError('handoff must change owner')
        if from_role not in OFFICE_ROLES or to_role not in OFFICE_ROLES: raise ValueError('unknown office')
        now_iso=now_iso or _now(); c=self.db._connection()
        try:
            c.execute("BEGIN IMMEDIATE")
            row=c.execute("SELECT * FROM task_office_assignments WHERE task_id=?",(task_id,)).fetchone()
            if not row or row['state']!='active' or row['owner_role']!=from_role: raise OfficeAssignmentConflict(f"task {task_id} is not actively owned by {from_role}")
            count=int(row['handoff_count'])
            if count>=MAX_HANDOFFS: raise OfficeHandoffLimit(f"task {task_id} reached handoff limit {MAX_HANDOFFS}")
            c.execute("UPDATE task_office_assignments SET owner_role=?,assigned_by=?,reason=?,handoff_count=?,state='active',updated_at=? WHERE task_id=?",(to_role,from_role,reason,count+1,now_iso,task_id))
            self._handoff_event(task_id=task_id,from_role=from_role,to_role=to_role,event_type='handoff',reason=reason,occurred_at=now_iso,metadata={'handoff_count':count+1},conn=c)
            c.commit()
        except Exception:
            c.rollback(); raise
        return self.get_assignment(task_id)
    def release_task(self,task_id,*,owner_role,reason,now_iso=None):
        now_iso=now_iso or _now(); c=self.db._connection()
        try:
            c.execute("BEGIN IMMEDIATE")
            row=c.execute("SELECT * FROM task_office_assignments WHERE task_id=?",(task_id,)).fetchone()
            if not row or row['state']!='active' or row['owner_role']!=owner_role:
                c.rollback(); return
            c.execute("UPDATE task_office_assignments SET state='released',updated_at=? WHERE task_id=?",(now_iso,task_id))
            self._handoff_event(task_id=task_id,from_role=owner_role,to_role=owner_role,event_type='released',reason=reason,occurred_at=now_iso,conn=c)
            c.commit()
        except Exception:
            c.rollback(); raise
    def ensure_trigger_assignments(self,*,now_iso=None):
        now_iso=now_iso or _now(); c=self.db._connection(); rows=c.execute("""SELECT f.task_id,d.owner_role,d.trigger_id FROM trigger_firings f JOIN trigger_definitions d ON d.trigger_id=f.trigger_id JOIN tasks t ON t.id=f.task_id LEFT JOIN task_office_assignments a ON a.task_id=f.task_id WHERE a.task_id IS NULL AND t.status IN ('new','running','blocked','failed')""").fetchall(); n=0
        for r in rows: self.assign_task(r['task_id'],r['owner_role'],assigned_by=f"trigger:{r['trigger_id']}",reason='durable trigger ownership',now_iso=now_iso); n+=1
        return n
    def assign_new_unowned_to_orchestra(self,*,now_iso=None):
        now_iso=now_iso or _now(); c=self.db._connection(); rows=c.execute("""SELECT t.id FROM tasks t LEFT JOIN trigger_firings f ON f.task_id=t.id LEFT JOIN task_office_assignments a ON a.task_id=t.id WHERE t.status='new' AND f.task_id IS NULL AND a.task_id IS NULL ORDER BY t.created_at,t.id""").fetchall()
        for r in rows: self.assign_task(r['id'],'orchestra',assigned_by='stillpointd',reason='unowned queued work enters Orchestra triage',now_iso=now_iso)
        return len(rows)
    def release_terminal_assignments(self,*,now_iso=None):
        now_iso=now_iso or _now(); c=self.db._connection(); rows=c.execute("""SELECT a.task_id,a.owner_role,t.status FROM task_office_assignments a JOIN tasks t ON t.id=a.task_id WHERE a.state='active' AND t.status IN ('completed','rejected','reconciled_effect','reconciled_no_effect')""").fetchall()
        for r in rows: self.release_task(r['task_id'],owner_role=r['owner_role'],reason=f"terminal task status: {r['status']}",now_iso=now_iso)
        return len(rows)
    def assignment_counts(self):
        rows=self.db._connection().execute("SELECT owner_role,COUNT(*) AS n FROM task_office_assignments WHERE state='active' GROUP BY owner_role ORDER BY owner_role").fetchall(); return {str(r['owner_role']):int(r['n']) for r in rows}
