import json,sqlite3,tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from stillpoint.signal_service import SignalServiceConfig
from stillpoint.signal_status import SignalStatusInspector
NOW=datetime(2026,9,17,22,0,tzinfo=timezone.utc)
def iso(d):return d.isoformat()
class DB:
 def __init__(self):
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row;self.c.executescript('''
 CREATE TABLE signal_gmail_mailboxes(account TEXT PRIMARY KEY,history_id TEXT,status TEXT,bootstrap_completed_at TEXT,last_polled_at TEXT,last_success_at TEXT,last_error TEXT,updated_at TEXT);
 CREATE TABLE signal_gmail_poll_receipts(receipt_id TEXT PRIMARY KEY,account TEXT,mode TEXT,started_at TEXT,finished_at TEXT,start_history_id TEXT,end_history_id TEXT,messages_seen INTEGER,tasks_created INTEGER,status TEXT,error TEXT);
 CREATE TABLE trigger_definitions(trigger_id TEXT PRIMARY KEY,owner_role TEXT,trigger_kind TEXT,source TEXT,event_type TEXT,goal_template TEXT,project TEXT,status TEXT,valid_from TEXT,review_by TEXT,next_run_at TEXT,interval_seconds INTEGER,max_runs INTEGER,run_count INTEGER,catch_up_policy TEXT,metadata_json TEXT,created_at TEXT,updated_at TEXT);
 CREATE TABLE standing_delegations(delegation_id TEXT PRIMARY KEY,delegate_role TEXT,issuer TEXT,policy_basis TEXT,purpose TEXT,claim_envelope_ids_json TEXT,allowed_action_types_json TEXT,continuation_conditions_json TEXT,execution_conditions_json TEXT,exclusions_json TEXT,release_conditions_json TEXT,valid_from TEXT,review_by TEXT,status TEXT,supersedes_delegation_id TEXT,created_at TEXT,updated_at TEXT);
 CREATE TABLE worker_instances(worker_id TEXT PRIMARY KEY,role TEXT,started_at TEXT,last_heartbeat_at TEXT,status TEXT,metadata_json TEXT);
 CREATE TABLE tasks(id TEXT PRIMARY KEY,status TEXT,created_at TEXT,updated_at TEXT,goal TEXT,project TEXT);
 CREATE TABLE trigger_firings(firing_id TEXT PRIMARY KEY,trigger_id TEXT,event_id TEXT,scheduled_for TEXT,task_id TEXT,idempotency_key TEXT,fired_at TEXT);
 CREATE TABLE signal_email_decisions(decision_id TEXT PRIMARY KEY,task_id TEXT,event_id TEXT,message_id TEXT,account TEXT,sender TEXT,reply_target TEXT,disposition TEXT,classification TEXT,requires_human INTEGER,reason TEXT,facts_json TEXT,artifact_id TEXT,action_id TEXT,created_at TEXT);
 CREATE TABLE action_requests(id TEXT PRIMARY KEY,status TEXT);
 CREATE TABLE action_dispatches(action_id TEXT PRIMARY KEY,state TEXT);
 ''')
 def _connection(self):return self.c
class Tests(unittest.TestCase):
 def setUp(self):
  self.td=tempfile.TemporaryDirectory();root=Path(self.td.name);facts=root/'facts.json';facts.write_text(json.dumps({'observed_at':iso(NOW-timedelta(minutes=1)),'valid_until':iso(NOW+timedelta(minutes=30)),'facts':{'policy':True}}))
  self.cfg=SignalServiceConfig(root=root,provider_name='xai',model='m',gmail_account='signal@example.com',gmail_access_token='secret',delegation_id='del',trigger_id='trig',facts_file=facts,worker_id='w')
  self.db=DB();c=self.db.c
  c.execute("insert into signal_gmail_mailboxes values(?,?,?,?,?,?,?,?)",('signal@example.com','h','active',iso(NOW-timedelta(hours=1)),iso(NOW),iso(NOW),None,iso(NOW)))
  c.execute("insert into signal_gmail_poll_receipts values(?,?,?,?,?,?,?,?,?,?,?)",('p','signal@example.com','history',iso(NOW),iso(NOW),'h0','h1',1,1,'succeeded',None))
  c.execute("insert into trigger_definitions values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",('trig','signal','event','gmail','message_received','g',None,'active',iso(NOW-timedelta(days=1)),iso(NOW+timedelta(days=2)),None,None,None,0,'coalesce','{}',iso(NOW),iso(NOW)))
  c.execute("insert into standing_delegations values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",('del','signal','CEO','p','p','[\"env\"]','[\"send_email\"]','[]','[]','[]','[\"review\"]',iso(NOW-timedelta(days=1)),iso(NOW+timedelta(days=2)),'active',None,iso(NOW),iso(NOW)))
  c.execute("insert into worker_instances values(?,?,?,?,?,?)",('w','signal',iso(NOW-timedelta(hours=1)),iso(NOW),'active','{}'));c.commit()
 def tearDown(self):self.td.cleanup()
 def snap(self,**kw):return SignalStatusInspector(db=self.db,config=self.cfg,now_fn=lambda:NOW,**kw).snapshot()
 def test_healthy_state_is_ok(self):self.assertEqual(self.snap(review_warning_seconds=3600,facts_warning_seconds=60)['health'],'ok')
 def test_resync_is_critical(self):
  self.db.c.execute("update signal_gmail_mailboxes set status='resync_required'");self.db.c.commit();s=self.snap();self.assertEqual(s['health'],'critical');self.assertIn('GMAIL_RESYNC_REQUIRED',[a['code'] for a in s['attention']])
 def test_stale_worker_is_critical(self):
  self.db.c.execute("update worker_instances set last_heartbeat_at=?",(iso(NOW-timedelta(hours=1)),));self.db.c.commit();s=self.snap(worker_stale_seconds=60);self.assertIn('SIGNAL_WORKER_STALE',[a['code'] for a in s['attention']])
 def test_uncertain_dispatch_is_critical(self):
  c=self.db.c;c.execute("insert into tasks values('t','completed',?,?,?,?)",(iso(NOW),iso(NOW),'g','signal'));c.execute("insert into trigger_firings values('f','trig',NULL,NULL,'t','i',?)",(iso(NOW),));c.execute("insert into action_requests values('a','uncertain')");c.execute("insert into signal_email_decisions values('d','t','e','m','signal@example.com','x','x','draft_reply','routine',0,'','{}','art','a',?)",(iso(NOW),));c.execute("insert into action_dispatches values('a','uncertain')");c.commit();s=self.snap();self.assertEqual(s['uncertain_dispatches'],1);self.assertIn('UNCERTAIN_EXTERNAL_EFFECT',[a['code'] for a in s['attention']])
 def test_human_review_queue_surfaces_attention(self):
  c=self.db.c;c.execute("insert into tasks values('t','blocked',?,?,?,?)",(iso(NOW),iso(NOW),'g','signal'));c.execute("insert into trigger_firings values('f','trig',NULL,NULL,'t','i',?)",(iso(NOW),));c.execute("insert into signal_email_decisions values('d','t','e','m','signal@example.com','x','x','human_review','legal',1,'r','{}',NULL,NULL,?)",(iso(NOW),));c.commit();s=self.snap();self.assertEqual(s['health'],'attention');self.assertIn('HUMAN_REVIEW_QUEUE',[a['code'] for a in s['attention']])
 def test_facts_expiring_warns(self):
  self.cfg.facts_file.write_text(json.dumps({'observed_at':iso(NOW-timedelta(minutes=1)),'valid_until':iso(NOW+timedelta(seconds=30)),'facts':{'policy':True}}));s=self.snap(facts_warning_seconds=60);self.assertIn('CONTINUATION_FACTS_EXPIRING',[a['code'] for a in s['attention']])
 def test_snapshot_is_read_only(self):
  before=self.db.c.total_changes;self.snap();after=self.db.c.total_changes;self.assertEqual(before,after)
if __name__=='__main__':unittest.main()
