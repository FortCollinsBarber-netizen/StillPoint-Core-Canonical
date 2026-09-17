import hashlib,json,sqlite3,tempfile,unittest
from pathlib import Path
from stillpoint.signal_email import SignalInboxExecutor,SignalDraftDecision
T='2026-09-17T20:00:00+00:00'
class DB:
 def __init__(self,p):self.conn=sqlite3.connect(p);self.conn.row_factory=sqlite3.Row
 def _connection(self):return self.conn
 def close(self):self.conn.close()
 def update_task(self,tid,**kw):
  if not kw:return
  self.conn.execute('update tasks set '+','.join(k+'=?' for k in kw)+' where id=?',(*kw.values(),tid));self.conn.commit()
 def add_run(self,task_id,agent_id,phase,output,**kw):
  rid='r'+hashlib.sha256((task_id+phase).encode()).hexdigest()[:8];self.conn.execute('insert or ignore into agent_runs(id,task_id,agent_id,phase,output,stage_key) values(?,?,?,?,?,?)',(rid,task_id,agent_id,phase,output,kw.get('stage_key','')));self.conn.commit();return rid
 def get_run_by_stage_key(self,k):
  r=self.conn.execute('select * from agent_runs where stage_key=?',(k,)).fetchone();return dict(r) if r else None
 def add_artifact(self,**kw):
  aid='a'+str(self.conn.execute('select count(*) from artifacts').fetchone()[0]+1);self.conn.execute('insert into artifacts values(?,?,?,?,?,?,?,?,?)',(aid,kw['task_id'],kw['kind'],kw['name'],kw['sha256'],kw['produced_by_run_id'],kw['phase'],1,kw.get('project')));self.conn.commit();return aid
 def list_artifacts(self,tid):return [dict(x) for x in self.conn.execute('select * from artifacts where task_id=?',(tid,)).fetchall()]
 def get_artifact(self,aid):
  r=self.conn.execute('select * from artifacts where id=?',(aid,)).fetchone();return dict(r) if r else None
 def find_action_request_by_idempotency(self,k):
  r=self.conn.execute('select * from action_requests where idempotency_key=?',(k,)).fetchone();return dict(r) if r else None
 def add_action_request(self,r):
  self.conn.execute('insert into action_requests(id,task_id,action_type,target,scope_json,artifact_refs_json,approval_required,approval_id,expires_at,issued_at,idempotency_key,success_criteria_json,authority_revision,status) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(r.action_id,r.task_id,r.action_type,r.target,json.dumps(r.scope),json.dumps([x.__dict__ for x in r.artifact_refs]),1,None,r.expires_at,r.issued_at,r.idempotency_key,json.dumps(r.success_criteria),r.authority_revision,'waiting_approval'));self.conn.commit();return r.action_id
 def get_action_request(self,aid):
  r=self.conn.execute('select * from action_requests where id=?',(aid,)).fetchone();return dict(r) if r else None
class Tr:
 def __init__(self,p):self.p=p
 def context_for_task(self,t):return {'source':'gmail','event_type':'message_received','event_id':'e1','payload':self.p}
class R:
 def __init__(self,d):self.d=d
 def draft(self,m,task_id):return self.d
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=DB(Path(self.tmp.name)/'d');c=self.db.conn;c.executescript('''
 CREATE TABLE tasks(id TEXT PRIMARY KEY,status TEXT,error TEXT,final_output TEXT,approval_reason TEXT);INSERT INTO tasks(id,status) VALUES('t1','new');
 CREATE TABLE agent_runs(id TEXT PRIMARY KEY,task_id TEXT,agent_id TEXT,phase TEXT,output TEXT,stage_key TEXT UNIQUE);
 CREATE TABLE artifacts(id TEXT PRIMARY KEY,task_id TEXT,kind TEXT,name TEXT,sha256 TEXT,produced_by_run_id TEXT,phase TEXT,version INTEGER,project TEXT);
 CREATE TABLE action_requests(id TEXT PRIMARY KEY,task_id TEXT,action_type TEXT,target TEXT,scope_json TEXT,artifact_refs_json TEXT,approval_required INTEGER,approval_id TEXT,expires_at TEXT,issued_at TEXT,idempotency_key TEXT UNIQUE,success_criteria_json TEXT,authority_revision TEXT,status TEXT);
 ''');c.executescript((Path(__file__).parents[1]/'migrations'/'017_signal_email_preparation.sql').read_text());c.executescript((Path(__file__).parents[1]/'migrations'/'019_provider_neutral_mailboxes.sql').read_text());c.commit()
  self.m={'message_id':'m1','thread_id':'th1','from_address':'alice@example.com','from':'Alice <alice@example.com>','reply_to':'','subject':'Meeting','snippet':'Tuesday?','text_plain':'Tuesday?','cc':'','has_attachments':False,'text_plain_truncated':False,'authentication_results':'dmarc=pass','auto_submitted':'','precedence':'','list_unsubscribe':''}
 def tearDown(self):self.db.close();self.tmp.cleanup()
 def ex(self,d,p=None):return SignalInboxExecutor(db=self.db,trigger_coordinator=Tr(p or self.m),account='signal@example.com',responder=R(d))
 def test_routine_creates_waiting_action_not_warrant(self):
  r=self.ex(SignalDraftDecision('draft_reply','scheduling','Tuesday works.')).execute('t1',now_iso=T);self.assertEqual(r['disposition'],'draft_reply');a=self.db.conn.execute('select * from action_requests').fetchone();self.assertEqual(a['status'],'waiting_approval');self.assertEqual(a['approval_required'],1);self.assertIn('to alice@example.com',a['target'])
 def test_human_review_creates_no_action(self):
  r=self.ex(SignalDraftDecision('human_review','contract',reason='contract',requires_human=True)).execute('t1',now_iso=T);self.assertEqual(r['disposition'],'human_review');self.assertEqual(self.db.conn.execute('select count(*) from action_requests').fetchone()[0],0);self.assertEqual(self.db.conn.execute("select status from tasks where id='t1'").fetchone()[0],'blocked')
 def test_noreply_suppressed_before_model(self):
  p=dict(self.m,from_address='no-reply@example.com');r=self.ex(SignalDraftDecision('draft_reply','routine','x'),p).execute('t1',now_iso=T);self.assertEqual(r['disposition'],'no_reply');self.assertEqual(self.db.conn.execute('select count(*) from action_requests').fetchone()[0],0)
 def test_list_mail_suppressed(self):
  p=dict(self.m,list_unsubscribe='<x>');r=self.ex(SignalDraftDecision('draft_reply','routine','x'),p).execute('t1',now_iso=T);self.assertEqual(r['disposition'],'no_reply')
 def test_reply_to_becomes_exact_proposed_target(self):
  p=dict(self.m,reply_to='Support <support@example.com>');r=self.ex(SignalDraftDecision('draft_reply','routine','ok'),p).execute('t1',now_iso=T);self.assertEqual(r['disposition'],'human_review');self.assertEqual(self.db.conn.execute('select count(*) from action_requests').fetchone()[0],0)
 def test_reexecution_is_idempotent(self):
  ex=self.ex(SignalDraftDecision('draft_reply','routine','ok'));a=ex.execute('t1',now_iso=T);b=ex.execute('t1',now_iso=T);self.assertTrue(b['reused']);self.assertEqual(self.db.conn.execute('select count(*) from action_requests').fetchone()[0],1);self.assertEqual(self.db.conn.execute('select count(*) from artifacts').fetchone()[0],1)
 def test_decision_history_append_only(self):
  self.ex(SignalDraftDecision('no_reply','not_needed')).execute('t1',now_iso=T);did=self.db.conn.execute('select decision_id from signal_email_decisions').fetchone()[0]
  with self.assertRaises(sqlite3.DatabaseError):self.db.conn.execute("update signal_email_decisions set classification='x' where decision_id=?",(did,))
  self.db.conn.rollback()
if __name__=='__main__':unittest.main()
