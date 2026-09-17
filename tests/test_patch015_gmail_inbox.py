import base64,json,sqlite3,tempfile,unittest,urllib.error
from pathlib import Path
from stillpoint.triggers import TaskTriggerCoordinator
from stillpoint.adapters.gmail_inbox import SignalGmailInboxPoller,GmailHistoryExpired
T='2026-09-17T19:00:00+00:00'

def enc(s):return base64.urlsafe_b64encode(s.encode()).decode().rstrip('=')
class Resp:
    def __init__(self,obj):self.raw=json.dumps(obj).encode()
    def __enter__(self):return self
    def __exit__(self,*a):pass
    def read(self):return self.raw
class Fake:
    def __init__(self,routes):self.routes=routes;self.requests=[]
    def __call__(self,req,timeout=0):
        self.requests.append(req)
        key=req.full_url
        val=self.routes.get(key)
        if isinstance(val,Exception):raise val
        if val is None: raise AssertionError('unexpected '+key)
        return Resp(val)
class DB:
    def __init__(self,p):self.conn=sqlite3.connect(p);self.conn.row_factory=sqlite3.Row
    def _connection(self):return self.conn
    def close(self):self.conn.close()

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.db=DB(Path(self.tmp.name)/'d.sqlite'); c=self.db.conn
        c.executescript('''CREATE TABLE tasks(id TEXT PRIMARY KEY,created_at TEXT,updated_at TEXT,goal TEXT,project TEXT,status TEXT); CREATE TABLE temporal_warrants(warrant_id TEXT PRIMARY KEY); CREATE TABLE action_requests(id TEXT PRIMARY KEY,task_id TEXT);''')
        for f in ['014_schedules_and_event_triggers.sql','016_signal_gmail_inbox.sql']:c.executescript((Path(__file__).parents[1]/'migrations'/f).read_text())
        c.commit(); self.tr=TaskTriggerCoordinator(self.db); self.tr.create_event_trigger(owner_role='signal',source='gmail',event_type='message_received',goal_template='Handle Gmail {event_id}',project='signal',valid_from='2026-09-17T00:00:00+00:00',review_by='2026-10-17T00:00:00+00:00',trigger_id='gmail-trigger')
        self.account='signal@example.com'; self.base='https://gmail.googleapis.com/gmail/v1/users/signal%40example.com'
    def tearDown(self):self.db.close();self.tmp.cleanup()
    def msg(self,mid='m1',hist='101'):
        return {'id':mid,'threadId':'th1','historyId':hist,'internalDate':'1789668000000','snippet':'hello','payload':{'mimeType':'multipart/alternative','headers':[{'name':'From','value':'Alice <alice@example.com>'},{'name':'To','value':self.account},{'name':'Subject','value':'Meeting'},{'name':'Message-ID','value':'<x@example.com>'}], 'parts':[{'mimeType':'text/plain','body':{'data':enc('Can we meet Tuesday?')}}]}}
    def poller(self,fake):return SignalGmailInboxPoller(db=self.db,trigger_coordinator=self.tr,account=self.account,access_token='tok',urlopen=fake)
    def test_bootstrap_creates_signal_task_not_authority(self):
        routes={self.base+'/profile':{'historyId':'100'},self.base+'/messages?labelIds=INBOX&maxResults=100':{'messages':[{'id':'m1'}]},self.base+'/messages/m1?format=full':self.msg()};f=Fake(routes)
        r=self.poller(f).poll(now_iso=T);self.assertEqual(r['tasks_created'],1);self.assertEqual(self.db.conn.execute('select count(*) from tasks').fetchone()[0],1);self.assertEqual(self.db.conn.execute('select count(*) from temporal_warrants').fetchone()[0],0);self.assertEqual(self.db.conn.execute('select count(*) from action_requests').fetchone()[0],0);self.assertTrue(all(x.get_method()=='GET' for x in f.requests))
    def test_bootstrap_payload_contains_plain_text(self):
        routes={self.base+'/profile':{'historyId':'100'},self.base+'/messages?labelIds=INBOX&maxResults=100':{'messages':[{'id':'m1'}]},self.base+'/messages/m1?format=full':self.msg()};self.poller(Fake(routes)).poll(now_iso=T)
        p=json.loads(self.db.conn.execute('select payload_json from inbound_events').fetchone()[0]);self.assertEqual(p['from_address'],'alice@example.com');self.assertEqual(p['text_plain'],'Can we meet Tuesday?')
    def test_history_addition_advances_cursor_after_ingest(self):
        c=self.db.conn;c.execute("insert into signal_gmail_mailboxes(account,history_id,status,updated_at) values(?,?,?,?)",(self.account,'100','active',T));c.commit()
        hist=self.base+'/history?'+__import__('urllib.parse').parse.urlencode([('startHistoryId','100'),('historyTypes','messageAdded'),('labelId','INBOX'),('maxResults','100')])
        routes={hist:{'historyId':'105','history':[{'messagesAdded':[{'message':{'id':'m2','labelIds':['INBOX']}}]}]},self.base+'/messages/m2?format=full':self.msg('m2','105')};r=self.poller(Fake(routes)).poll(now_iso=T);self.assertEqual(r['history_id'],'105');self.assertEqual(r['tasks_created'],1)
    def test_duplicate_resync_does_not_duplicate_task(self):
        routes={self.base+'/profile':{'historyId':'100'},self.base+'/messages?labelIds=INBOX&maxResults=100':{'messages':[{'id':'m1'}]},self.base+'/messages/m1?format=full':self.msg()};p=self.poller(Fake(routes));p.poll(now_iso=T);p2=self.poller(Fake(routes));r=p2.resync(now_iso=T);self.assertEqual(r['tasks_created'],0);self.assertEqual(self.db.conn.execute('select count(*) from tasks').fetchone()[0],1)
    def test_expired_history_requires_resync_and_preserves_cursor(self):
        c=self.db.conn;c.execute("insert into signal_gmail_mailboxes(account,history_id,status,updated_at) values(?,?,?,?)",(self.account,'100','active',T));c.commit()
        hist=self.base+'/history?'+__import__('urllib.parse').parse.urlencode([('startHistoryId','100'),('historyTypes','messageAdded'),('labelId','INBOX'),('maxResults','100')])
        err=urllib.error.HTTPError(hist,404,'gone',{},None);p=self.poller(Fake({hist:err}))
        with self.assertRaises(GmailHistoryExpired):p.poll(now_iso=T)
        row=c.execute('select * from signal_gmail_mailboxes').fetchone();self.assertEqual(row['history_id'],'100');self.assertEqual(row['status'],'resync_required')
    def test_receipts_append_only(self):
        routes={self.base+'/profile':{'historyId':'100'},self.base+'/messages?labelIds=INBOX&maxResults=100':{'messages':[]}};self.poller(Fake(routes)).poll(now_iso=T);rid=self.db.conn.execute('select receipt_id from signal_gmail_poll_receipts').fetchone()[0]
        with self.assertRaises(sqlite3.DatabaseError):self.db.conn.execute("update signal_gmail_poll_receipts set status='failed' where receipt_id=?",(rid,))
        self.db.conn.rollback()
if __name__=='__main__':unittest.main()
