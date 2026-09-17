"""Provider-neutral Signal mailbox intake and fleet composition.

A mailbox event creates internal work only. It never grants standing, creates a
warrant, or sends a reply. Each mailbox is bound to provider + account + jurisdiction.
"""
from __future__ import annotations

import hashlib,json,uuid
from dataclasses import dataclass
from datetime import datetime,timezone
from typing import Any

from .mail_contracts import MailboxIdentity

def _now():return datetime.now(timezone.utc)
def _iso(dt):return dt.astimezone(timezone.utc).isoformat()
def _mailbox_id(identity:MailboxIdentity)->str:
    raw=f"{identity.provider}|{identity.account}|{identity.jurisdiction}"
    return "mailbox-"+hashlib.sha256(raw.encode()).hexdigest()[:20]

class SignalMailPoller:
    def __init__(self, *, db, trigger_coordinator, transport, trigger_id:str):
        self.db=db;self.triggers=trigger_coordinator;self.transport=transport;self.identity=transport.identity;self.trigger_id=trigger_id
        if not trigger_id.strip():raise ValueError('mail trigger id required')
        self.mailbox_id=_mailbox_id(self.identity)

    def ensure_registered(self, *, now_iso:str|None=None):
        now_iso=now_iso or _iso(_now());c=self.db._connection()
        trigger=c.execute('select owner_role,trigger_kind,source,event_type,status from trigger_definitions where trigger_id=?',(self.trigger_id,)).fetchone()
        if not trigger:raise ValueError('configured mailbox trigger does not exist')
        if trigger['owner_role']!='signal' or trigger['trigger_kind']!='event' or trigger['source']!=self.identity.provider or trigger['event_type']!='message_received' or trigger['status']!='active':
            raise ValueError('configured trigger does not match mailbox provider/event')
        row=c.execute('select * from signal_mailboxes where mailbox_id=?',(self.mailbox_id,)).fetchone()
        if row:
            if row['provider']!=self.identity.provider or row['account']!=self.identity.account or row['jurisdiction']!=self.identity.jurisdiction or row['trigger_id']!=self.trigger_id:
                raise ValueError('mailbox identity conflict')
            return dict(row)
        c.execute('''insert into signal_mailboxes(mailbox_id,provider,account,jurisdiction,cursor,status,trigger_id,created_at,updated_at) values(?,?,?,?,?,?,?,?,?)''',(self.mailbox_id,self.identity.provider,self.identity.account,self.identity.jurisdiction,None,'active',self.trigger_id,now_iso,now_iso));c.commit()
        return dict(c.execute('select * from signal_mailboxes where mailbox_id=?',(self.mailbox_id,)).fetchone())

    def poll(self, *, now_iso:str|None=None, limit:int=50)->dict[str,Any]:
        now_iso=now_iso or _iso(_now());state=self.ensure_registered(now_iso=now_iso);before=state.get('cursor');started=now_iso;c=self.db._connection()
        if state.get('status')!='active':return {'status':state['status'],'mailbox_id':self.mailbox_id,'messages_seen':0,'tasks_created':0}
        try:
            messages,after=self.transport.fetch_since(before,limit=limit);tasks=[]
            for m in messages:
                payload=m.to_event_payload();payload['jurisdiction']=self.identity.jurisdiction
                dedupe=f"{self.identity.provider}|{self.identity.account}|{m.provider_message_id or m.message_id}"
                event=self.triggers.ingest_event(source=self.identity.provider,event_type='message_received',dedupe_key=dedupe,occurred_at=m.observed_at or now_iso,received_at=now_iso,payload=payload)
                tasks.extend(self.triggers.fire_event(event.event_id,now_iso=now_iso))
            c.execute('update signal_mailboxes set cursor=?,last_polled_at=?,last_error=null,updated_at=? where mailbox_id=?',(after,now_iso,now_iso,self.mailbox_id))
            rid='mailpoll-'+uuid.uuid4().hex[:20]
            c.execute('''insert into signal_mail_poll_receipts(receipt_id,mailbox_id,provider,cursor_before,cursor_after,messages_seen,tasks_created,status,error,started_at,finished_at) values(?,?,?,?,?,?,?,?,?,?,?)''',(rid,self.mailbox_id,self.identity.provider,before,after,len(messages),len(tasks),'ok',None,started,now_iso));c.commit()
            return {'status':'ok','mailbox_id':self.mailbox_id,'messages_seen':len(messages),'tasks_created':len(tasks),'task_ids':tasks,'cursor':after}
        except Exception as exc:
            c.rollback();finished=now_iso;rid='mailpoll-'+uuid.uuid4().hex[:20]
            c.execute('update signal_mailboxes set last_polled_at=?,last_error=?,updated_at=? where mailbox_id=?',(finished,f'{type(exc).__name__}: {exc}',finished,self.mailbox_id))
            c.execute('''insert into signal_mail_poll_receipts(receipt_id,mailbox_id,provider,cursor_before,cursor_after,messages_seen,tasks_created,status,error,started_at,finished_at) values(?,?,?,?,?,?,?,?,?,?,?)''',(rid,self.mailbox_id,self.identity.provider,before,before,0,0,'error',f'{type(exc).__name__}: {exc}',started,finished));c.commit();raise

@dataclass
class SignalMailboxFleet:
    employees: dict[str,Any]

    @classmethod
    def from_employees(cls, pairs:list[tuple[MailboxIdentity,Any]]):
        out={}
        for identity,employee in pairs:
            key=identity.authority_subject
            if key in out:raise ValueError(f'duplicate mailbox jurisdiction: {key}')
            out[key]=employee
        if not out:raise ValueError('at least one mailbox employee required')
        return cls(out)

    def tick_all(self)->dict[str,Any]:
        results={}
        for key,employee in self.employees.items():
            try:results[key]=employee.tick()
            except Exception as exc:results[key]={'status':'degraded','error':f'{type(exc).__name__}: {exc}'}
        return results
