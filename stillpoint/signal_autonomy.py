"""Bridge a prepared Signal reply into standing-delegation consideration.

This module does not define CEO policy. It evaluates one already-prepared exact
ActionRequest against a caller-selected standing delegation and records the
assessment before asking Patch 012 to issue a one-use warrant.
"""
from __future__ import annotations
import json
from typing import Any

class SignalAutonomyError(RuntimeError): pass

class SignalStandingAuthorizer:
    def __init__(self, *, db, delegation_store, envelope_store, warrant_issuer):
        self.db=db;self.delegations=delegation_store;self.envelopes=envelope_store;self.issuer=warrant_issuer

    def authorize_prepared_reply(self, *, action_id:str, delegation_id:str, now_iso:str,
                                 continuation_facts:dict[str,Any], envelope_facts:dict[str,dict[str,Any]]|None=None,
                                 additional_execution_facts:dict[str,Any]|None=None,
                                 max_evaluation_age_seconds:int=60, warrant_ttl_seconds:int=300):
        conn=self.db._connection(); action=conn.execute('select * from action_requests where id=?',(action_id,)).fetchone()
        if not action:raise KeyError(action_id)
        action=dict(action)
        if action['action_type']!='send_email':raise SignalAutonomyError('Signal email authorizer only accepts send_email')
        decision=conn.execute('select * from signal_email_decisions where action_id=?',(action_id,)).fetchone()
        if not decision:raise SignalAutonomyError('prepared Signal decision required')
        decision=dict(decision)
        if decision['disposition']!='draft_reply' or int(decision['requires_human'])!=0:raise SignalAutonomyError('Signal decision is not eligible for autonomous consideration')
        delegation=self.delegations.get(delegation_id)
        if not delegation:raise SignalAutonomyError('standing delegation not found')
        if delegation.delegate_role!='signal':raise SignalAutonomyError('delegation does not belong to Signal')
        envs={}
        for eid in delegation.claim_envelope_ids:
            env=self.envelopes.get(eid)
            if env:envs[eid]=env
        stored_facts=json.loads(decision['facts_json'] or '{}')
        keys=set(decision.keys())
        execution={
            'signal_email':{
                'prepared':True,'requires_human':False,'classification':decision['classification'],
                'sender':decision['sender'],'reply_target':decision['reply_target'],'account':decision['account'],
                'provider':decision['mail_provider'] if 'mail_provider' in keys else 'gmail',
                'jurisdiction':decision['mail_jurisdiction'] if 'mail_jurisdiction' in keys else 'legacy',
                'message_id':decision['message_id'],'action_id':action_id,'action_type':action['action_type'],'action_target':action['target'],
            },
            'triage':stored_facts,
        }
        if additional_execution_facts: execution.update(additional_execution_facts)
        assessment=delegation.assess(now_iso=now_iso,continuation_facts=continuation_facts,action_type=action['action_type'],execution_facts=execution,envelopes=envs,envelope_facts=envelope_facts or {},proposed_use_by_envelope={eid:'send_email' for eid in delegation.claim_envelope_ids})
        evaluation_id=self.delegations.record_assessment(delegation_id=delegation_id,assessment=assessment,evaluated_at=now_iso,continuation_facts=continuation_facts,execution_facts=execution,action_id=action_id,action_type=action['action_type'],action_target=action['target'])
        if not assessment.eligible_for_warrant_consideration:
            return {'authorized':False,'evaluation_id':evaluation_id,'assessment':assessment,'warrant':None}
        warrant=self.issuer.authorize_waiting_action(action_id=action_id,delegation_id=delegation_id,evaluation_id=evaluation_id,now_iso=now_iso,ttl_seconds=warrant_ttl_seconds,max_evaluation_age_seconds=max_evaluation_age_seconds)
        return {'authorized':True,'evaluation_id':evaluation_id,'assessment':assessment,'warrant':warrant}
