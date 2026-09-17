import base64,unittest
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
from stillpoint.contracts.models import ActionRequest,ArtifactRef
from stillpoint.signal_email import SignalEmailSafetyGate,SignalInboxExecutor,SignalDraftDecision
from stillpoint.adapters.gmail_inbox import SignalGmailInboxPoller
from stillpoint.signal_service import _require_delegation,SignalServiceConfigurationError
NOW=datetime(2026,9,17,22,0,tzinfo=timezone.utc);PAST=(NOW-timedelta(hours=1)).isoformat();FUT=(NOW+timedelta(hours=1)).isoformat()
class Tests(unittest.TestCase):
 def test_safe_verified_plain_mail_passes_deterministic_gate(self):
  m={'from_address':'alice@example.com','reply_to':'','cc':'','has_attachments':False,'text_plain_truncated':False,'authentication_results':'mx.google; spf=pass; dkim=pass; dmarc=pass','subject':'Meeting time','snippet':'Can we meet Tuesday?','text_plain':'Can we meet Tuesday at 2?'}
  self.assertEqual(SignalEmailSafetyGate().inbound_reasons(m),[])
 def test_reply_to_spoof_group_attachment_truncation_and_auth_fail_force_review(self):
  m={'from_address':'alice@example.com','reply_to':'Mallory <mallory@evil.example>','cc':'team@example.com','has_attachments':True,'text_plain_truncated':True,'authentication_results':'spf=fail; dkim=fail; dmarc=fail','subject':'hello','snippet':'x','text_plain':'x'}
  r=SignalEmailSafetyGate().inbound_reasons(m)
  for code in ('reply_to_differs_from_sender','group_or_cc_mail','attachments_present','body_truncated','sender_authentication_not_verified'):self.assertIn(code,r)
 def test_high_risk_inbound_forces_review(self):
  m={'from_address':'a@b.com','cc':'','has_attachments':False,'text_plain_truncated':False,'authentication_results':'dmarc=pass','subject':'Bank details','snippet':'','text_plain':'Please wire $500 to this routing number.'}
  self.assertIn('high_risk_content',SignalEmailSafetyGate().inbound_reasons(m))
 def test_high_risk_outbound_commitment_forces_review(self):
  self.assertEqual(SignalEmailSafetyGate().outbound_reasons('We agree to refund $500.'),['high_risk_reply_commitment'])
 def test_gmail_normalization_preserves_auth_and_attachment_evidence(self):
  p=SignalGmailInboxPoller(db=SimpleNamespace(),trigger_coordinator=SimpleNamespace(),account='signal@example.com',access_token='tok')
  body=base64.urlsafe_b64encode(b'hello').decode().rstrip('=')
  msg={'id':'m1','threadId':'t1','payload':{'mimeType':'multipart/mixed','headers':[{'name':'From','value':'Alice <alice@example.com>'},{'name':'Authentication-Results','value':'spf=pass; dkim=pass; dmarc=pass'},{'name':'Return-Path','value':'<bounce@example.com>'}], 'parts':[{'mimeType':'text/plain','body':{'data':body}},{'mimeType':'application/pdf','filename':'invoice.pdf','body':{'attachmentId':'att1'}}]}}
  n=p._normalize(msg);self.assertTrue(n['has_attachments']);self.assertEqual(n['attachments'][0]['filename'],'invoice.pdf');self.assertIn('dmarc=pass',n['authentication_results']);self.assertEqual(n['return_path'],'<bounce@example.com>')
 def test_executor_blocks_reply_to_mismatch_before_model_or_action(self):
  import sqlite3,json,hashlib,tempfile
  class D:
   def __init__(self):
    self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row;self.c.executescript("""
CREATE TABLE tasks(id TEXT PRIMARY KEY,status TEXT,error TEXT,final_output TEXT,approval_reason TEXT);INSERT INTO tasks(id,status) VALUES('t','new');
CREATE TABLE signal_email_decisions(decision_id TEXT PRIMARY KEY,task_id TEXT,event_id TEXT,message_id TEXT,account TEXT,sender TEXT,reply_target TEXT,disposition TEXT,classification TEXT,requires_human INTEGER,reason TEXT,facts_json TEXT,artifact_id TEXT,action_id TEXT,created_at TEXT,mail_provider TEXT,mail_jurisdiction TEXT);
CREATE TABLE agent_runs(id TEXT PRIMARY KEY,task_id TEXT,agent_id TEXT,phase TEXT,output TEXT,stage_key TEXT);CREATE TABLE artifacts(id TEXT PRIMARY KEY,task_id TEXT,kind TEXT,name TEXT,sha256 TEXT,produced_by_run_id TEXT,phase TEXT,version INTEGER,project TEXT);CREATE TABLE action_requests(id TEXT PRIMARY KEY,idempotency_key TEXT);
""")
   def _connection(self):return self.c
   def update_task(self,tid,**kw):self.c.execute('update tasks set '+','.join(k+'=?' for k in kw)+' where id=?',(*kw.values(),tid));self.c.commit()
  class Tr:
   def context_for_task(self,t):return {'source':'gmail','event_type':'message_received','event_id':'e','payload':{'provider':'gmail','account':'signal@example.com','jurisdiction':'legacy','message_id':'m','from_address':'alice@example.com','reply_to':'Mallory <m@evil.example>','cc':'','has_attachments':False,'text_plain_truncated':False,'authentication_results':'dmarc=pass','subject':'Meeting','snippet':'Tuesday?','text_plain':'Tuesday?','auto_submitted':'','precedence':'','list_unsubscribe':''}}
  class R:
   called=False
   def draft(self,*a,**k):self.called=True;return SignalDraftDecision('draft_reply','scheduling','ok')
  db=D();r=R();out=SignalInboxExecutor(db=db,trigger_coordinator=Tr(),account='signal@example.com',responder=r).execute('t',now_iso=NOW.isoformat());self.assertEqual(out['disposition'],'human_review');self.assertFalse(r.called);self.assertEqual(db.c.execute('select count(*) from action_requests').fetchone()[0],0)

 def conditions(self,classification=True):
  C=lambda k,o,e:SimpleNamespace(key=k,operator=SimpleNamespace(value=o),expected=e)
  out=[C('signal_email.account','eq','signal@example.com'),C('signal_email.prepared','eq',True),C('signal_email.requires_human','eq',False)]
  if classification:out.append(C('signal_email.classification','in',['scheduling','acknowledgement']))
  return out
 def test_production_delegation_requires_machine_enforced_classification_bound(self):
  d=SimpleNamespace(status=SimpleNamespace(value='active'),delegate_role='signal',valid_from=PAST,review_by=FUT,allowed_action_types=['send_email'],execution_conditions=self.conditions(False))
  store=SimpleNamespace(get=lambda _:d);cfg=SimpleNamespace(delegation_id='d',gmail_account='signal@example.com')
  with self.assertRaises(SignalServiceConfigurationError):_require_delegation(store,cfg,now_iso=NOW.isoformat())
  d.execution_conditions=self.conditions(True);self.assertIs(_require_delegation(store,cfg,now_iso=NOW.isoformat()),d)
if __name__=='__main__':unittest.main()
