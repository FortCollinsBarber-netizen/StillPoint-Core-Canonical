import json,sqlite3,unittest
from types import SimpleNamespace
from pathlib import Path
from stillpoint.signal_autonomy import SignalStandingAuthorizer,SignalAutonomyError
T='2026-09-17T20:00:00+00:00'
class DB:
 def __init__(self):
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row;self.c.executescript('''
 CREATE TABLE action_requests(id TEXT PRIMARY KEY,action_type TEXT,target TEXT,status TEXT);
 CREATE TABLE signal_email_decisions(action_id TEXT,disposition TEXT,requires_human INTEGER,classification TEXT,sender TEXT,reply_target TEXT,account TEXT,message_id TEXT,facts_json TEXT);
 INSERT INTO action_requests VALUES('a1','send_email','target','waiting_approval');
 INSERT INTO signal_email_decisions VALUES('a1','draft_reply',0,'routine','alice@example.com','alice@example.com','signal@example.com','m1','{"model":{"x":1}}');
 ''')
 def _connection(self):return self.c
class Assessment:
 def __init__(self,ok):self.eligible_for_warrant_consideration=ok;self.standing=SimpleNamespace(value='current' if ok else 'review_required');self.action_in_scope=ok;self.failed_conditions=[] if ok else ['x'];self.supporting_envelopes=['env'];self.note='n'
class Delegation:
 delegate_role='signal';claim_envelope_ids=['env']
 def __init__(self,ok=True):self.ok=ok;self.seen=None
 def assess(self,**kw):self.seen=kw;return Assessment(self.ok)
class DStore:
 def __init__(self,d):self.d=d;self.records=[]
 def get(self,i):return self.d
 def record_assessment(self,**kw):self.records.append(kw);return 'eval1'
class EStore:
 def get(self,i):return SimpleNamespace(envelope_id=i)
class Issuer:
 def __init__(self):self.calls=[]
 def authorize_waiting_action(self,**kw):self.calls.append(kw);return SimpleNamespace(warrant_id='w1')
class Tests(unittest.TestCase):
 def build(self,ok=True):
  self.db=DB();self.d=Delegation(ok);self.ds=DStore(self.d);self.es=EStore();self.iss=Issuer();return SignalStandingAuthorizer(db=self.db,delegation_store=self.ds,envelope_store=self.es,warrant_issuer=self.iss)
 def test_current_assessment_issues_exact_action_warrant(self):
  a=self.build(True);r=a.authorize_prepared_reply(action_id='a1',delegation_id='del',now_iso=T,continuation_facts={'company_policy_current':True});self.assertTrue(r['authorized']);self.assertEqual(self.iss.calls[0]['action_id'],'a1');self.assertEqual(self.ds.records[0]['action_target'],'target');self.assertEqual(self.d.seen['execution_facts']['signal_email']['message_id'],'m1')
 def test_failed_assessment_records_but_does_not_issue(self):
  a=self.build(False);r=a.authorize_prepared_reply(action_id='a1',delegation_id='del',now_iso=T,continuation_facts={});self.assertFalse(r['authorized']);self.assertEqual(len(self.ds.records),1);self.assertEqual(self.iss.calls,[])
 def test_human_review_decision_is_ineligible(self):
  a=self.build();self.db.c.execute("update signal_email_decisions set requires_human=1,disposition='human_review'");self.db.c.commit()
  with self.assertRaises(SignalAutonomyError):a.authorize_prepared_reply(action_id='a1',delegation_id='del',now_iso=T,continuation_facts={})
 def test_wrong_role_delegation_is_rejected(self):
  a=self.build();self.d.delegate_role='ledger'
  with self.assertRaises(SignalAutonomyError):a.authorize_prepared_reply(action_id='a1',delegation_id='del',now_iso=T,continuation_facts={})
if __name__=='__main__':unittest.main()
