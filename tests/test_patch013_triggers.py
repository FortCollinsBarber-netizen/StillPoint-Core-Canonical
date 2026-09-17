from __future__ import annotations
import sqlite3,unittest
from pathlib import Path
from stillpoint.triggers import TaskTriggerCoordinator
T0='2026-09-17T16:00:00+00:00';T1='2026-09-17T16:01:00+00:00';T5='2026-09-17T16:05:00+00:00';REVIEW='2026-10-01T00:00:00+00:00'
class DB:
 def __init__(self,c):self.c=c
 def _connection(self):return self.c
class TriggerTests(unittest.TestCase):
 def setUp(self):
  c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');self.c=c
  c.executescript('''CREATE TABLE tasks(id TEXT PRIMARY KEY,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,goal TEXT NOT NULL,project TEXT,status TEXT NOT NULL); CREATE TABLE temporal_warrants(warrant_id TEXT PRIMARY KEY); CREATE TABLE action_requests(id TEXT PRIMARY KEY,task_id TEXT);''')
  c.executescript((Path(__file__).resolve().parents[1]/'migrations'/'014_schedules_and_event_triggers.sql').read_text())
  self.t=TaskTriggerCoordinator(DB(c))
 def tearDown(self):self.c.close()
 def test_event_ingestion_is_deduplicated_and_fires_once(self):
  self.t.create_event_trigger(owner_role='signal',source='gmail',event_type='message.received',goal_template='Handle {event_type} {event_id}',project='signal',valid_from=T0,review_by=REVIEW,trigger_id='tr-email')
  a=self.t.ingest_event(source='gmail',event_type='message.received',dedupe_key='gmail:msg-1',occurred_at=T0,received_at=T0,payload={'message_id':'msg-1'})
  b=self.t.ingest_event(source='gmail',event_type='message.received',dedupe_key='gmail:msg-1',occurred_at=T0,received_at=T0,payload={'message_id':'msg-1'})
  self.assertEqual(a.event_id,b.event_id);self.assertEqual(self.c.execute('select count(*) from inbound_events').fetchone()[0],1)
  first=self.t.fire_event(a.event_id,now_iso=T1);second=self.t.fire_event(a.event_id,now_iso=T1)
  self.assertEqual(len(first),1);self.assertEqual(second,[]);self.assertEqual(self.c.execute('select count(*) from tasks').fetchone()[0],1)
 def test_trigger_creates_no_external_authority(self):
  self.t.create_event_trigger(owner_role='signal',source='gmail',event_type='message.received',goal_template='Handle {event_id}',project='signal',valid_from=T0,review_by=REVIEW)
  e=self.t.ingest_event(source='gmail',event_type='message.received',dedupe_key='k',occurred_at=T0,received_at=T0,payload={})
  self.t.fire_event(e.event_id,now_iso=T1)
  self.assertEqual(self.c.execute('select count(*) from temporal_warrants').fetchone()[0],0);self.assertEqual(self.c.execute('select count(*) from action_requests').fetchone()[0],0)
 def test_interval_schedule_coalesces_downtime_and_advances_future(self):
  self.t.create_interval_trigger(owner_role='research',goal_template='Scheduled research',project='research',valid_from=T0,review_by=REVIEW,next_run_at=T1,interval_seconds=60,trigger_id='tr-sched')
  ids=self.t.fire_due(now_iso=T5);self.assertEqual(len(ids),1)
  row=self.c.execute("select * from trigger_definitions where trigger_id='tr-sched'").fetchone();self.assertEqual(row['run_count'],1);self.assertGreater(row['next_run_at'],T5)
  self.assertEqual(self.t.fire_due(now_iso=T5),[])
 def test_review_boundary_stops_new_work(self):
  self.t.create_event_trigger(owner_role='signal',source='gmail',event_type='message.received',goal_template='Handle {event_id}',project='signal',valid_from=T0,review_by=T1)
  e=self.t.ingest_event(source='gmail',event_type='message.received',dedupe_key='k2',occurred_at=T0,received_at=T0,payload={})
  self.assertEqual(self.t.fire_event(e.event_id,now_iso=T1),[])
 def test_firing_context_recovers_event_payload(self):
  self.t.create_event_trigger(owner_role='signal',source='gmail',event_type='message.received',goal_template='Handle {event_id}',project='signal',valid_from=T0,review_by=REVIEW)
  e=self.t.ingest_event(source='gmail',event_type='message.received',dedupe_key='k3',occurred_at=T0,received_at=T0,payload={'message_id':'abc'})
  task=self.t.fire_event(e.event_id,now_iso=T1)[0];ctx=self.t.context_for_task(task);self.assertEqual(ctx['payload']['message_id'],'abc');self.assertEqual(ctx['owner_role'],'signal')
 def test_inbound_event_history_is_append_only(self):
  e=self.t.ingest_event(source='gmail',event_type='message.received',dedupe_key='k4',occurred_at=T0,received_at=T0,payload={})
  with self.assertRaises(sqlite3.DatabaseError):self.c.execute('delete from inbound_events where event_id=?',(e.event_id,))
  self.c.rollback()
if __name__=='__main__':unittest.main()
