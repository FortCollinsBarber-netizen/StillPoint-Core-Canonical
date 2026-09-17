"""Explicit CEO governance provisioning for Signal email autonomy.

This module is intentionally separate from the employee daemon. It validates and
persists a bounded standing-delegation policy only when the caller confirms the
exact canonical policy digest. Revisions are new policy objects; existing
standing is never silently broadened or overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass,field
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

from .temporal.envelope import ContinuationCondition,ConditionOperator

SCHEMA='stillpoint.signal-governance.v1'
CEO_ISSUER='CEO:Robert Emmanuel LaDay'
SAFE_AUTONOMOUS_CLASSIFICATIONS=frozenset({'scheduling','acknowledgement','routine_information'})

class SignalGovernanceError(RuntimeError):pass

def _parse(value:str)->datetime:
 try:dt=datetime.fromisoformat(str(value).replace('Z','+00:00'))
 except Exception as exc:raise SignalGovernanceError(f'invalid governance timestamp: {value!r}') from exc
 if dt.tzinfo is None or dt.utcoffset() is None:raise SignalGovernanceError('governance timestamps must be timezone-aware')
 return dt.astimezone(timezone.utc)
def _canon(v:Any)->str:return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str)
def _conditions(raw)->list[ContinuationCondition]:return [ContinuationCondition(key=str(x['key']),operator=ConditionOperator(str(x.get('operator') or 'eq')),expected=x.get('expected'),note=str(x.get('note') or '')) for x in raw or []]

def _condition_dict(c:ContinuationCondition):return c.to_dict()

@dataclass(frozen=True)
class SignalGovernanceSpec:
 spec_id:str
 gmail_account:str
 delegation_id:str
 trigger_id:str
 policy_basis:str
 purpose:str
 claim_envelope_ids:list[str]
 allowed_classifications:list[str]
 continuation_conditions:list[ContinuationCondition]
 additional_execution_conditions:list[ContinuationCondition]
 exclusions:list[str]
 release_conditions:list[str]
 valid_from:str
 review_by:str
 trigger_valid_from:str
 trigger_review_by:str
 facts_snapshot:dict[str,Any]
 issuer:str=CEO_ISSUER
 schema:str=SCHEMA

 @classmethod
 def from_dict(cls,raw:dict[str,Any]):
  if not isinstance(raw,dict):raise SignalGovernanceError('governance spec must be object')
  if raw.get('schema')!=SCHEMA:raise SignalGovernanceError(f'schema must be {SCHEMA}')
  issuer=str(raw.get('issuer') or '')
  if issuer!=CEO_ISSUER:raise SignalGovernanceError(f'issuer must be {CEO_ISSUER}')
  ids={k:str(raw.get(k) or '').strip() for k in ('spec_id','gmail_account','delegation_id','trigger_id','policy_basis','purpose')}
  if any(not v for v in ids.values()):raise SignalGovernanceError('spec_id, gmail_account, delegation_id, trigger_id, policy_basis, and purpose are required')
  if '@' not in ids['gmail_account']:raise SignalGovernanceError('gmail_account must be explicit email address')
  env=[str(x).strip() for x in raw.get('claim_envelope_ids') or [] if str(x).strip()]
  if not env:raise SignalGovernanceError('claim_envelope_ids required')
  classes=[str(x).strip() for x in raw.get('allowed_classifications') or [] if str(x).strip()]
  if not classes or not set(classes).issubset(SAFE_AUTONOMOUS_CLASSIFICATIONS):raise SignalGovernanceError('allowed_classifications must be a non-empty subset of safe routine classes')
  cont=_conditions(raw.get('continuation_conditions'))
  if not cont:raise SignalGovernanceError('continuation_conditions required')
  extra=_conditions(raw.get('additional_execution_conditions'))
  excl=[str(x).strip() for x in raw.get('exclusions') or [] if str(x).strip()]
  rel=[str(x).strip() for x in raw.get('release_conditions') or [] if str(x).strip()]
  if not excl or not rel:raise SignalGovernanceError('exclusions and release_conditions required')
  vf=str(raw.get('valid_from') or '');rb=str(raw.get('review_by') or '');tvf=str(raw.get('trigger_valid_from') or vf);trb=str(raw.get('trigger_review_by') or rb)
  if _parse(rb)<=_parse(vf):raise SignalGovernanceError('review_by must follow valid_from')
  if _parse(trb)<=_parse(tvf):raise SignalGovernanceError('trigger_review_by must follow trigger_valid_from')
  if _parse(tvf)<_parse(vf) or _parse(trb)>_parse(rb):raise SignalGovernanceError('trigger authority must fit inside delegation review interval')
  facts=raw.get('facts_snapshot')
  if not isinstance(facts,dict):raise SignalGovernanceError('facts_snapshot required')
  observed=str(facts.get('observed_at') or '');until=str(facts.get('valid_until') or '')
  if not observed or not until or not isinstance(facts.get('facts'),dict):raise SignalGovernanceError('facts_snapshot requires observed_at, valid_until, facts')
  if _parse(until)<=_parse(observed):raise SignalGovernanceError('facts_snapshot valid_until must follow observed_at')
  if _parse(until)>_parse(rb):raise SignalGovernanceError('facts_snapshot cannot outlive delegation review interval')
  return cls(spec_id=ids['spec_id'],gmail_account=ids['gmail_account'].lower(),delegation_id=ids['delegation_id'],trigger_id=ids['trigger_id'],policy_basis=ids['policy_basis'],purpose=ids['purpose'],claim_envelope_ids=env,allowed_classifications=classes,continuation_conditions=cont,additional_execution_conditions=extra,exclusions=excl,release_conditions=rel,valid_from=vf,review_by=rb,trigger_valid_from=tvf,trigger_review_by=trb,facts_snapshot=facts,issuer=issuer)

 @classmethod
 def load(cls,path:Path):
  try:raw=json.loads(Path(path).read_text(encoding='utf-8'))
  except Exception as exc:raise SignalGovernanceError(f'invalid governance spec file: {path}') from exc
  return cls.from_dict(raw)

 def execution_conditions(self)->list[ContinuationCondition]:
  base=[
   ContinuationCondition('signal_email.account',ConditionOperator.EQ,self.gmail_account,'bind exact Gmail identity'),
   ContinuationCondition('signal_email.prepared',ConditionOperator.EQ,True,'reply must be prepared'),
   ContinuationCondition('signal_email.requires_human',ConditionOperator.EQ,False,'human-review work is excluded'),
   ContinuationCondition('signal_email.classification',ConditionOperator.IN,list(self.allowed_classifications),'finite autonomous classification set'),
  ]
  keys={(c.key,c.operator.value) for c in base}
  for c in self.additional_execution_conditions:
   if (c.key,c.operator.value) in keys:raise SignalGovernanceError(f'additional execution condition duplicates protected condition: {c.key}')
  return base+list(self.additional_execution_conditions)

 def canonical_dict(self)->dict[str,Any]:
  return {'schema':self.schema,'issuer':self.issuer,'spec_id':self.spec_id,'gmail_account':self.gmail_account,'delegation_id':self.delegation_id,'trigger_id':self.trigger_id,'policy_basis':self.policy_basis,'purpose':self.purpose,'claim_envelope_ids':list(self.claim_envelope_ids),'allowed_classifications':list(self.allowed_classifications),'continuation_conditions':[_condition_dict(c) for c in self.continuation_conditions],'additional_execution_conditions':[_condition_dict(c) for c in self.additional_execution_conditions],'exclusions':list(self.exclusions),'release_conditions':list(self.release_conditions),'valid_from':self.valid_from,'review_by':self.review_by,'trigger_valid_from':self.trigger_valid_from,'trigger_review_by':self.trigger_review_by,'facts_snapshot':self.facts_snapshot}
 def digest(self)->str:return hashlib.sha256(_canon(self.canonical_dict()).encode('utf-8')).hexdigest()

class SignalGovernanceProvisioner:
 def __init__(self,db):self.db=db
 def preview(self,spec:SignalGovernanceSpec)->dict[str,Any]:
  c=self.db._connection();missing=[];former=[]
  for eid in spec.claim_envelope_ids:
   r=c.execute('select status from temporal_claim_envelopes where envelope_id=?',(eid,)).fetchone()
   if not r:missing.append(eid)
   elif r['status']!='active':former.append(eid)
  d=c.execute('select policy_basis,status from standing_delegations where delegation_id=?',(spec.delegation_id,)).fetchone()
  t=c.execute('select metadata_json,status from trigger_definitions where trigger_id=?',(spec.trigger_id,)).fetchone()
  digest=spec.digest();conflicts=[]
  if d and f'signal_governance_spec:{digest}' not in str(d['policy_basis']):conflicts.append('delegation_id_already_used_by_different_policy')
  if t:
   try:meta=json.loads(t['metadata_json'] or '{}')
   except Exception:meta={}
   if meta.get('signal_governance_sha256')!=digest:conflicts.append('trigger_id_already_used_by_different_policy')
  return {'spec_id':spec.spec_id,'sha256':digest,'ready_to_apply':not(missing or former or conflicts),'missing_envelopes':missing,'noncurrent_envelopes':former,'conflicts':conflicts,'existing_delegation':bool(d),'existing_trigger':bool(t),'authority_change':True}

 def apply(self,spec:SignalGovernanceSpec,*,facts_file:Path,expected_sha256:str,ceo_confirmed:bool)->dict[str,Any]:
  digest=spec.digest()
  if not ceo_confirmed:raise SignalGovernanceError('explicit CEO confirmation required')
  if expected_sha256!=digest:raise SignalGovernanceError('CEO confirmation digest does not match exact governance spec')
  preview=self.preview(spec)
  if not preview['ready_to_apply']:raise SignalGovernanceError('governance spec is not applicable: '+_canon(preview))
  facts_file=Path(facts_file)
  if not facts_file.is_absolute():raise SignalGovernanceError('facts_file must be absolute')
  if facts_file.is_symlink():raise SignalGovernanceError('facts_file may not be a symlink')
  facts_file.parent.mkdir(parents=True,exist_ok=True)
  payload=_canon(spec.facts_snapshot)+'\n';tmp=Path(tempfile.mkstemp(prefix='.signal-facts-',dir=facts_file.parent)[1])
  try:
   tmp.write_text(payload,encoding='utf-8')
   c=self.db._connection();now=datetime.now(timezone.utc).isoformat();policy=f'{spec.policy_basis};signal_governance_spec:{digest}'
   try:
    c.execute('BEGIN IMMEDIATE')
    # Re-check exact envelope standing inside the authority-changing transaction.
    for eid in spec.claim_envelope_ids:
     r=c.execute("select status from temporal_claim_envelopes where envelope_id=?",(eid,)).fetchone()
     if not r or r['status']!='active':raise SignalGovernanceError(f'supporting envelope changed before apply: {eid}')
    d=c.execute('select policy_basis from standing_delegations where delegation_id=?',(spec.delegation_id,)).fetchone()
    t=c.execute('select metadata_json from trigger_definitions where trigger_id=?',(spec.trigger_id,)).fetchone()
    if not d:
     c.execute('''INSERT INTO standing_delegations(delegation_id,delegate_role,issuer,policy_basis,purpose,claim_envelope_ids_json,allowed_action_types_json,continuation_conditions_json,execution_conditions_json,exclusions_json,release_conditions_json,valid_from,review_by,status,supersedes_delegation_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(spec.delegation_id,'signal',spec.issuer,policy,spec.purpose,_canon(spec.claim_envelope_ids),_canon(['send_email']),_canon([x.to_dict() for x in spec.continuation_conditions]),_canon([x.to_dict() for x in spec.execution_conditions()]),_canon(spec.exclusions),_canon(spec.release_conditions),spec.valid_from,spec.review_by,'active',None,now,now))
    elif f'signal_governance_spec:{digest}' not in str(d['policy_basis']):raise SignalGovernanceError('delegation conflict during apply')
    metadata={'signal_governance_spec_id':spec.spec_id,'signal_governance_sha256':digest,'gmail_account':spec.gmail_account}
    if not t:
     c.execute('''INSERT INTO trigger_definitions(trigger_id,owner_role,trigger_kind,source,event_type,goal_template,project,status,valid_from,review_by,next_run_at,interval_seconds,max_runs,run_count,catch_up_policy,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(spec.trigger_id,'signal','event','gmail','message_received','Handle Signal Gmail message {event_id}','signal','active',spec.trigger_valid_from,spec.trigger_review_by,None,None,None,0,'coalesce',_canon(metadata),now,now))
    else:
     try:existing=json.loads(t['metadata_json'] or '{}')
     except Exception:existing={}
     if existing.get('signal_governance_sha256')!=digest:raise SignalGovernanceError('trigger conflict during apply')
    c.commit()
   except Exception:
    c.rollback();raise
   os.replace(tmp,facts_file)
   return {'applied':True,'sha256':digest,'delegation_id':spec.delegation_id,'trigger_id':spec.trigger_id,'facts_file':str(facts_file),'reused_existing':preview['existing_delegation'] and preview['existing_trigger']}
  finally:
   if tmp.exists():
    try:tmp.unlink()
    except Exception:pass

def main(argv=None)->int:
 p=argparse.ArgumentParser(prog='python -m stillpoint.signal_governance');sub=p.add_subparsers(dest='cmd',required=True)
 for name in ('preview','apply'):
  sp=sub.add_parser(name);sp.add_argument('spec');sp.add_argument('--facts-file',required=(name=='apply'))
  if name=='apply':sp.add_argument('--confirm-sha',required=True);sp.add_argument('--confirm-ceo',action='store_true')
 a=p.parse_args(argv)
 from .db import CompanyDB
 from .signal_service import SignalServiceConfig
 root=Path(os.getenv('STILLPOINT_ROOT') or Path.cwd()).resolve();db=CompanyDB(root/'state'/'company.sqlite')
 try:
  spec=SignalGovernanceSpec.load(Path(a.spec));prov=SignalGovernanceProvisioner(db)
  if a.cmd=='preview':out=prov.preview(spec)
  else:out=prov.apply(spec,facts_file=Path(a.facts_file),expected_sha256=a.confirm_sha,ceo_confirmed=a.confirm_ceo)
  print(json.dumps(out,indent=2,default=str));return 0 if (out.get('ready_to_apply',True) and out.get('applied',True)) else 1
 except Exception as exc:
  print(json.dumps({'ok':False,'error':f'{type(exc).__name__}: {exc}'},indent=2));return 2
 finally:db.close()
if __name__=='__main__':raise SystemExit(main())
