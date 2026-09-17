"""Read-only release gate for autonomous Signal email.

A production adapter being technically available is not enough. The gate binds
runtime readiness back to the exact CEO governance digest and refuses release
when authority/evidence/state disagree or any external effect remains uncertain.
"""
from __future__ import annotations

import json
from dataclasses import dataclass,field
from typing import Any,Callable

from .signal_governance import SignalGovernanceSpec
from .signal_service import SignalServiceConfig,validate_signal_service

@dataclass(frozen=True)
class GateCheck:
 name:str
 ok:bool
 detail:str=''
 def to_dict(self):return {'name':self.name,'ok':self.ok,'detail':self.detail}

@dataclass(frozen=True)
class SignalReleaseGateResult:
 verdict:str
 checks:list[GateCheck]=field(default_factory=list)
 @property
 def passed(self):return self.verdict=='PASS'
 def to_dict(self):return {'verdict':self.verdict,'checks':[c.to_dict() for c in self.checks]}

class SignalReleaseGate:
 def __init__(self,*,db,config:SignalServiceConfig,governance_spec:SignalGovernanceSpec,validator:Callable=validate_signal_service):
  self.db=db;self.config=config;self.spec=governance_spec;self.validator=validator
 def _check(self,name,fn)->GateCheck:
  try:
   value=fn();
   if isinstance(value,tuple):ok,detail=value
   else:ok,detail=bool(value),''
   return GateCheck(name,bool(ok),str(detail))
  except Exception as exc:return GateCheck(name,False,f'{type(exc).__name__}: {exc}')
 def run(self)->SignalReleaseGateResult:
  digest=self.spec.digest();c=self.db._connection();checks=[]
  checks.append(self._check('service_readiness',lambda:(bool(self.validator(self.config).get('ready')), 'static configuration/current standing valid')))
  checks.append(self._check('governance_identity',lambda:(self.spec.gmail_account==self.config.gmail_account and self.spec.delegation_id==self.config.delegation_id and self.spec.trigger_id==self.config.trigger_id,'configured service matches governance spec')))
  def delegation_digest():
   r=c.execute('select policy_basis,status from standing_delegations where delegation_id=?',(self.config.delegation_id,)).fetchone();return (bool(r) and r['status']=='active' and f'signal_governance_spec:{digest}' in str(r['policy_basis']), 'active delegation binds exact governance digest')
  checks.append(self._check('delegation_digest',delegation_digest))
  def trigger_digest():
   r=c.execute('select metadata_json,status from trigger_definitions where trigger_id=?',(self.config.trigger_id,)).fetchone();meta=json.loads(r['metadata_json'] or '{}') if r else {};return (bool(r) and r['status']=='active' and meta.get('signal_governance_sha256')==digest,'active trigger binds exact governance digest')
  checks.append(self._check('trigger_digest',trigger_digest))
  def envelopes():
   bad=[]
   for eid in self.spec.claim_envelope_ids:
    r=c.execute('select status from temporal_claim_envelopes where envelope_id=?',(eid,)).fetchone()
    if not r or r['status']!='active':bad.append(eid)
   return (not bad,'all supporting envelopes current' if not bad else 'noncurrent:'+','.join(bad))
  checks.append(self._check('supporting_envelopes',envelopes))
  def uncertain():
   r=c.execute("""select count(*) n from action_dispatches d join signal_email_decisions s on s.action_id=d.action_id where s.account=? and d.state='uncertain'""",(self.config.gmail_account,)).fetchone();n=int(r['n'] if r else 0);return (n==0,f'uncertain_dispatches={n}')
  checks.append(self._check('no_uncertain_external_effects',uncertain))
  def lineage_conflicts():
   rows=c.execute("""select a.id from action_requests a join signal_email_decisions s on s.action_id=a.id where s.account=? and a.authorization_mode='standing_delegation' and (a.standing_delegation_id is null or a.standing_evaluation_id is null or a.warrant_id is null)""",(self.config.gmail_account,)).fetchall();return (len(rows)==0,f'incomplete_delegated_lineage={len(rows)}')
  checks.append(self._check('delegated_lineage_complete',lineage_conflicts))
  verdict='PASS' if all(x.ok for x in checks) else 'HALT'
  return SignalReleaseGateResult(verdict,checks)
