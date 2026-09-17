"""First complete StillPoint vertical employee: Signal email.

Composition only. No new authority primitive lives here. Signal observes Gmail,
claims its own internal tasks, prepares a reply proposal, evaluates the exact
ActionRequest against a CEO-selected standing delegation, obtains a one-use
warrant through Patch 012, and executes through the existing runtime/adapter gate.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime,timezone
from typing import Any,Callable

try:
    from .adapters.gmail_inbox import GmailHistoryExpired
except Exception:
    class GmailHistoryExpired(RuntimeError): pass

def _now():return datetime.now(timezone.utc)
def _iso(dt):return dt.astimezone(timezone.utc).isoformat()

@dataclass(frozen=True)
class SignalEmployeeTick:
    intake: dict[str,Any]
    work: dict[str,Any]|None

class SignalEmailEmployee:
    def __init__(self, *, poller, worker_service, preparer, authorizer, runtime, adapter_registry,
                 delegation_id:str, continuation_facts_provider:Callable[...,dict[str,Any]],
                 envelope_facts_provider:Callable[...,dict[str,dict[str,Any]]]|None=None,
                 execution_facts_provider:Callable[...,dict[str,Any]]|None=None,
                 now_fn:Callable[[],datetime]=_now):
        if not delegation_id.strip():raise ValueError('Signal standing delegation id required')
        self.poller=poller;self.worker=worker_service;self.preparer=preparer;self.authorizer=authorizer;self.runtime=runtime;self.adapters=adapter_registry
        self.delegation_id=delegation_id;self.continuation_facts_provider=continuation_facts_provider;self.envelope_facts_provider=envelope_facts_provider;self.execution_facts_provider=execution_facts_provider;self.now_fn=now_fn

    def _execute_task(self,task_id,guard):
        prepared=self.preparer.execute(task_id,guard=guard,now_iso=_iso(self.now_fn()))
        if prepared.get('disposition')!='draft_reply':return {'prepared':prepared,'authorized':False,'dispatched':False}
        action_id=prepared['action_id'];guard.assert_current(now_iso=_iso(self.now_fn()))
        continuation=self.continuation_facts_provider(task_id=task_id,action_id=action_id,prepared=prepared)
        envelope_facts=self.envelope_facts_provider(task_id=task_id,action_id=action_id,prepared=prepared) if self.envelope_facts_provider else None
        extra=self.execution_facts_provider(task_id=task_id,action_id=action_id,prepared=prepared) if self.execution_facts_provider else None
        auth=self.authorizer.authorize_prepared_reply(action_id=action_id,delegation_id=self.delegation_id,now_iso=_iso(self.now_fn()),continuation_facts=continuation,envelope_facts=envelope_facts,additional_execution_facts=extra)
        if not auth.get('authorized'):
            return {'prepared':prepared,'authorization':auth,'authorized':False,'dispatched':False}
        # Ownership and standing are independently rechecked before the runtime enters
        # the durable dispatch transaction. Patch 017 then rechecks standing inside it.
        guard.assert_current(now_iso=_iso(self.now_fn()))
        dispatched=self.runtime.execute_action(action_id,self.adapters,now_iso=_iso(self.now_fn()))
        return {'prepared':prepared,'authorization':auth,'authorized':True,'dispatched':True,'dispatch':dispatched}

    def tick(self)->SignalEmployeeTick:
        now=_iso(self.now_fn())
        try:intake=self.poller.poll(now_iso=now)
        except GmailHistoryExpired as exc:intake={'status':'resync_required','error':str(exc)}
        except Exception as exc:intake={'status':'degraded','error':f'{type(exc).__name__}: {exc}'}
        # Intake degradation does not strand already-durable work.
        work=self.worker.run_once(self._execute_task,now_iso=_iso(self.now_fn()))
        return SignalEmployeeTick(intake=intake,work=work)

    def serve(self, *, interval_seconds:float=10.0, stop_event:threading.Event|None=None):
        stop_event=stop_event or threading.Event()
        while not stop_event.is_set():
            try:self.tick()
            except Exception:
                # Worker service has already durably recorded task-level failures. A single
                # task/provider/adapter failure must not terminate the employee daemon.
                pass
            stop_event.wait(interval_seconds)
