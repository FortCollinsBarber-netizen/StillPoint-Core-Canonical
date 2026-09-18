import sqlite3,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace

from stillpoint.workers import DurableWorkerCoordinator, LeaseLost
from stillpoint.worker_service import PersistentWorkerService,WorkerServiceConfig,LeaseHeartbeatGuard

T0='2026-09-17T18:00:00+00:00'

class DB:
    def __init__(self,path):
        self.path=Path(path); self.conn=sqlite3.connect(path); self.conn.row_factory=sqlite3.Row; self.migrations_dir=Path('/dev/null')
    def _connection(self): return self.conn
    def close(self): self.conn.close()
    def create_task(self,goal,project=None):
        tid='t'+str(self.conn.execute('select count(*) from tasks').fetchone()[0]+1); self.conn.execute('insert into tasks values(?,?,?,?,?,?)',(tid,T0,T0,goal,project,'new')); self.conn.commit(); return tid
    def get_task(self,tid):
        r=self.conn.execute('select * from tasks where id=?',(tid,)).fetchone(); return dict(r) if r else None

class Patch014Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.path=Path(self.tmp.name)/'db.sqlite'; self.db=DB(self.path)
        c=self.db.conn
        c.executescript('''
        CREATE TABLE tasks(id TEXT PRIMARY KEY,created_at TEXT,updated_at TEXT,goal TEXT,project TEXT,status TEXT);
        CREATE TABLE trigger_definitions(trigger_id TEXT PRIMARY KEY,owner_role TEXT);
        CREATE TABLE trigger_firings(firing_id TEXT PRIMARY KEY,trigger_id TEXT,event_id TEXT,scheduled_for TEXT,task_id TEXT UNIQUE,idempotency_key TEXT,fired_at TEXT);
        CREATE TABLE temporal_warrants(warrant_id TEXT PRIMARY KEY);
        CREATE TABLE action_requests(id TEXT PRIMARY KEY,task_id TEXT);
        ''')
        for f in ['010_autonomous_worker_runtime.sql','015_worker_service_runtime.sql']:
            c.executescript((Path(__file__).parent.parent/'migrations'/f).read_text())
        c.commit(); self.coord=DurableWorkerCoordinator(self.db); self.coord.register_worker(role='signal',worker_id='sig',now_iso=T0)
        self.cfg=WorkerServiceConfig(role='signal',lease_ttl_seconds=60,heartbeat_interval_seconds=10,retry_backoff_seconds=30,max_failures=2)
        self.service=PersistentWorkerService(db=self.db,coordinator=self.coord,coordinator_factory=lambda: DurableWorkerCoordinator(DB(self.path)),config=self.cfg,worker_id='sig')
    def tearDown(self): self.db.close();self.tmp.cleanup()
    def add_signal_task(self,status='new'):
        t=self.db.create_task('mail'); self.db.conn.execute('update tasks set status=? where id=?',(status,t)); self.db.conn.execute('insert or ignore into trigger_definitions values(?,?)',('tr','signal')); self.db.conn.execute('insert into trigger_firings values(?,?,?,?,?,?,?)',('f'+t,'tr',None,None,t,'i'+t,T0)); self.db.conn.commit(); return t
    def test_role_scoped_claim(self):
        t=self.add_signal_task(); lease=self.service.claim_next(now_iso=T0); self.assertEqual(lease.task_id,t)
    def test_unowned_task_excluded(self):
        self.db.create_task('x'); self.assertIsNone(self.service.claim_next(now_iso=T0))
    def test_run_once_records_success_and_releases(self):
        t=self.add_signal_task()
        def ex(task,guard): self.db.conn.execute("update tasks set status='completed' where id=?",(task,)); self.db.conn.commit(); return 'ok'
        r=self.service.run_once(ex,now_iso=T0); self.assertEqual(r['outcome'],'succeeded'); self.assertEqual(self.coord.get_lease(t).state,'released')
        ev=self.db.conn.execute('select event_type from worker_task_execution_events order by rowid').fetchall(); self.assertEqual([x[0] for x in ev],['started','succeeded'])
    def test_failed_task_not_auto_retry_by_default(self):
        t=self.add_signal_task('failed'); self.assertEqual(self.service.eligible_task_ids(now_iso=T0),[])
    def test_retry_can_be_enabled_and_exhausts(self):
        self.service.config=WorkerServiceConfig(role='signal',lease_ttl_seconds=60,heartbeat_interval_seconds=10,retry_backoff_seconds=0,max_failures=1,auto_retry_failed=True)
        t=self.add_signal_task('failed'); self.assertNotIn(t,self.service.eligible_task_ids(now_iso=T0)); self.service._set_retry(t,outcome='failed',now=__import__('datetime').datetime.fromisoformat(T0)); self.assertNotIn(t,self.service.eligible_task_ids(now_iso=T0))
    def test_service_creates_no_authority(self):
        self.add_signal_task(); before=self.db.conn.execute('select count(*) from temporal_warrants').fetchone()[0]
        self.service.run_once(lambda task,guard:'x',now_iso=T0)
        self.assertEqual(self.db.conn.execute('select count(*) from temporal_warrants').fetchone()[0],before)
        self.assertEqual(self.db.conn.execute('select count(*) from action_requests').fetchone()[0],0)
    def test_execution_events_append_only(self):
        self.add_signal_task(); self.service.run_once(lambda t,g:'x',now_iso=T0); eid=self.db.conn.execute('select event_id from worker_task_execution_events limit 1').fetchone()[0]
        with self.assertRaises(sqlite3.DatabaseError): self.db.conn.execute("update worker_task_execution_events set event_type='failed' where event_id=?",(eid,))
        self.db.conn.rollback()

    def test_serve_survives_task_exception_until_stopped(self):
        import threading
        self.add_signal_task(); stop=threading.Event(); calls=[]
        def ex(task,guard):
            calls.append(task); stop.set(); raise RuntimeError("boom")
        self.service.serve(ex,poll_interval_seconds=0.001,stop_event=stop)
        self.assertEqual(len(calls),1)
        self.assertEqual(self.db.conn.execute("select event_type from worker_task_execution_events order by rowid desc limit 1").fetchone()[0],"failed")

    def test_guard_detects_lost_lease(self):
        t=self.add_signal_task(); lease=self.service.claim_next(now_iso=T0); guard=LeaseHeartbeatGuard(coordinator_factory=lambda: DurableWorkerCoordinator(DB(self.path)),lease=lease,ttl_seconds=60,interval_seconds=10)
        self.db.conn.execute("update task_worker_leases set lease_token='other',generation=generation+1 where task_id=?",(t,)); self.db.conn.commit()
        with self.assertRaises(LeaseLost): guard.assert_current(now_iso=T0)

if __name__=='__main__': unittest.main()
