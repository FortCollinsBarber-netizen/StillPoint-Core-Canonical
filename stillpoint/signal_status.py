"""Read-only operational status surface for the Signal email employee.

Monitoring observes; it never authorizes. The inspector reads durable StillPoint
state and reports whether Signal is healthy, stale, blocked, nearing review, or
holding uncertain external effects. It performs no UPDATE/INSERT/DELETE.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from .signal_service import SignalServiceConfig, SnapshotFactsProvider, _parse_time, _iso, _now


@dataclass(frozen=True)
class AttentionItem:
    severity: str
    code: str
    message: str
    count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        out={"severity":self.severity,"code":self.code,"message":self.message}
        if self.count is not None:out["count"]=self.count
        return out


class SignalStatusInspector:
    def __init__(self, *, db, config: SignalServiceConfig, now_fn: Callable[[],datetime]=_now,
                 poll_stale_seconds:int=300, worker_stale_seconds:int=180,
                 facts_warning_seconds:int=900, review_warning_seconds:int=86400):
        self.db=db;self.config=config;self.now_fn=now_fn
        self.poll_stale_seconds=int(poll_stale_seconds);self.worker_stale_seconds=int(worker_stale_seconds)
        self.facts_warning_seconds=int(facts_warning_seconds);self.review_warning_seconds=int(review_warning_seconds)

    def _one(self,sql,args=()):
        row=self.db._connection().execute(sql,args).fetchone();return dict(row) if row else None
    def _all(self,sql,args=()):return [dict(r) for r in self.db._connection().execute(sql,args).fetchall()]
    def _seconds_until(self,value:str)->float:return (_parse_time(value)-self.now_fn().astimezone(timezone.utc)).total_seconds()
    def _age(self,value:str|None)->float|None:
        if not value:return None
        return (self.now_fn().astimezone(timezone.utc)-_parse_time(value)).total_seconds()

    def snapshot(self)->dict[str,Any]:
        now=self.now_fn().astimezone(timezone.utc);alerts:list[AttentionItem]=[]
        mailbox=self._one('SELECT * FROM signal_gmail_mailboxes WHERE account=?',(self.config.gmail_account,))
        poll=self._one('SELECT * FROM signal_gmail_poll_receipts WHERE account=? ORDER BY finished_at DESC,receipt_id DESC LIMIT 1',(self.config.gmail_account,))
        trigger=self._one('SELECT * FROM trigger_definitions WHERE trigger_id=?',(self.config.trigger_id,))
        delegation=self._one('SELECT * FROM standing_delegations WHERE delegation_id=?',(self.config.delegation_id,))
        workers=self._all("SELECT worker_id,status,started_at,last_heartbeat_at,metadata_json FROM worker_instances WHERE role='signal' ORDER BY last_heartbeat_at DESC,worker_id")
        task_counts={r['status']:int(r['n']) for r in self._all("""SELECT t.status,COUNT(*) n FROM tasks t JOIN trigger_firings f ON f.task_id=t.id JOIN trigger_definitions d ON d.trigger_id=f.trigger_id WHERE d.owner_role='signal' GROUP BY t.status""")}
        decision_counts={r['disposition']:int(r['n']) for r in self._all("SELECT disposition,COUNT(*) n FROM signal_email_decisions WHERE account=? GROUP BY disposition",(self.config.gmail_account,))}
        action_counts={r['status']:int(r['n']) for r in self._all("""SELECT a.status,COUNT(*) n FROM action_requests a JOIN signal_email_decisions s ON s.action_id=a.id WHERE s.account=? GROUP BY a.status""",(self.config.gmail_account,))}
        uncertain=int(self._one("""SELECT COUNT(*) n FROM action_dispatches d JOIN signal_email_decisions s ON s.action_id=d.action_id WHERE s.account=? AND d.state='uncertain'""",(self.config.gmail_account,))['n'])

        if not mailbox:alerts.append(AttentionItem('critical','MAILBOX_MISSING','Signal Gmail mailbox state is not initialized.'))
        else:
            if mailbox['status']=='resync_required':alerts.append(AttentionItem('critical','GMAIL_RESYNC_REQUIRED','Gmail history cursor expired; explicit resync is required.'))
            elif mailbox['status']=='paused':alerts.append(AttentionItem('warning','MAILBOX_PAUSED','Signal Gmail intake is paused.'))
            if mailbox.get('last_error'):alerts.append(AttentionItem('warning','GMAIL_LAST_ERROR',str(mailbox['last_error'])))
            age=self._age(mailbox.get('last_success_at'))
            if mailbox['status']=='active' and age is not None and age>self.poll_stale_seconds:alerts.append(AttentionItem('warning','GMAIL_POLL_STALE',f'Last successful Gmail poll is {int(age)} seconds old.'))

        active=[w for w in workers if w['status']=='active']
        if not active:alerts.append(AttentionItem('critical','NO_ACTIVE_SIGNAL_WORKER','No active Signal worker is registered.'))
        else:
            age=self._age(active[0].get('last_heartbeat_at'))
            if age is None or age>self.worker_stale_seconds:alerts.append(AttentionItem('critical','SIGNAL_WORKER_STALE',f'Newest active Signal worker heartbeat is stale ({int(age or 0)} seconds).'))

        if not delegation:alerts.append(AttentionItem('critical','DELEGATION_MISSING','Configured Signal standing delegation is missing.'))
        else:
            if delegation['status']!='active':alerts.append(AttentionItem('critical','DELEGATION_NOT_ACTIVE',f"Signal delegation status={delegation['status']}"))
            remain=self._seconds_until(delegation['review_by'])
            if remain<=0:alerts.append(AttentionItem('critical','DELEGATION_REVIEW_EXPIRED','Signal standing delegation review interval has ended.'))
            elif remain<self.review_warning_seconds:alerts.append(AttentionItem('warning','DELEGATION_REVIEW_DUE',f'Signal delegation review is due in {int(remain)} seconds.'))

        if not trigger:alerts.append(AttentionItem('critical','TRIGGER_MISSING','Configured Signal Gmail trigger is missing.'))
        else:
            if trigger['status']!='active':alerts.append(AttentionItem('warning','TRIGGER_NOT_ACTIVE',f"Signal Gmail trigger status={trigger['status']}"))
            remain=self._seconds_until(trigger['review_by'])
            if remain<=0:alerts.append(AttentionItem('critical','TRIGGER_REVIEW_EXPIRED','Signal Gmail trigger review interval has ended.'))
            elif remain<self.review_warning_seconds:alerts.append(AttentionItem('warning','TRIGGER_REVIEW_DUE',f'Signal Gmail trigger review is due in {int(remain)} seconds.'))

        facts_info=None
        try:
            snap=SnapshotFactsProvider(self.config.facts_file,now_fn=self.now_fn).snapshot();remain=self._seconds_until(snap.valid_until)
            facts_info={'observed_at':snap.observed_at,'valid_until':snap.valid_until,'source':snap.source}
            if remain<self.facts_warning_seconds:alerts.append(AttentionItem('warning','CONTINUATION_FACTS_EXPIRING',f'Continuation facts expire in {int(remain)} seconds.'))
        except Exception as exc:
            alerts.append(AttentionItem('critical','CONTINUATION_FACTS_NOT_CURRENT',str(exc)))

        human=int(decision_counts.get('human_review',0))
        blocked=int(task_counts.get('blocked',0))
        waiting=int(action_counts.get('waiting_approval',0))
        if human or blocked:alerts.append(AttentionItem('warning','HUMAN_REVIEW_QUEUE','Signal has work requiring human review.',max(human,blocked)))
        if waiting:alerts.append(AttentionItem('warning','WAITING_APPROVAL_QUEUE','Signal has prepared actions waiting for authority.',waiting))
        if uncertain:alerts.append(AttentionItem('critical','UNCERTAIN_EXTERNAL_EFFECT','Signal has external dispatches requiring reconciliation.',uncertain))

        severity='ok'
        if any(a.severity=='critical' for a in alerts):severity='critical'
        elif alerts:severity='attention'
        return {
            'as_of':_iso(now),'health':severity,'account':self.config.gmail_account,
            'delegation_id':self.config.delegation_id,'trigger_id':self.config.trigger_id,
            'mailbox':mailbox,'latest_poll':poll,'workers':workers,'task_counts':task_counts,
            'decision_counts':decision_counts,'action_counts':action_counts,'uncertain_dispatches':uncertain,
            'continuation_facts':facts_info,'attention':[a.to_dict() for a in alerts],
        }


def main(argv=None)->int:
    parser=argparse.ArgumentParser(prog='python -m stillpoint.signal_status');parser.parse_args(argv)
    from .db import CompanyDB
    try:config=SignalServiceConfig.from_env()
    except Exception as exc:
        print(json.dumps({'health':'critical','error':f'{type(exc).__name__}: {exc}'},indent=2));return 2
    db=CompanyDB(config.root/'state'/'company.sqlite')
    try:
        result=SignalStatusInspector(db=db,config=config).snapshot();print(json.dumps(result,indent=2,default=str));return 0 if result['health']=='ok' else 1
    finally:db.close()

if __name__=='__main__':raise SystemExit(main())
