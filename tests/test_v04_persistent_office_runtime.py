from __future__ import annotations
import json,sqlite3,tempfile,threading,time,unittest
from pathlib import Path
from stillpoint.db import CompanyDB
from stillpoint.office_runtime import OfficeAssignmentConflict,OfficeRuntimeCoordinator,OFFICE_ROLES
from stillpoint.providers.mock import MockProvider
from stillpoint.registry import AgentRegistry
from stillpoint.runtime import CompanyRuntime
from stillpoint.supervisor import CompanySupervisor,SupervisorConfig
from stillpoint.triggers import TaskTriggerCoordinator
from stillpoint.workers import DurableWorkerCoordinator
from stillpoint.worker_service import PersistentWorkerService,WorkerServiceConfig
ROOT=Path(__file__).resolve().parents[1]
def runtime(root): return CompanyRuntime(root=root,db=CompanyDB(root/"state"/"company.sqlite"),registry=AgentRegistry(ROOT/"config"/"agents.json"),provider=MockProvider(),default_model="mock",smart_routing=True,allowed_import_roots=[root])
class V04PersistentOfficeRuntimeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.db=CompanyDB(self.root/"state"/"company.sqlite");self.offices=OfficeRuntimeCoordinator(self.db);self.offices.initialize_offices()
 def tearDown(self):
  try:self.db.close()
  except Exception:pass
  self.tmp.cleanup()
 def test_schema20_and_all_office_states_exist(self): self.assertGreaterEqual(self.db.schema_version,20);self.assertEqual({r["role"] for r in self.offices.get_office_states()},set(OFFICE_ROLES))
 def test_assignment_cannot_silently_change_owner(self):
  t=self.db.create_task("Write","book");self.offices.assign_task(t,"author",assigned_by="test",reason="writing")
  with self.assertRaises(OfficeAssignmentConflict):self.offices.assign_task(t,"press",assigned_by="test",reason="publish")
 def test_handoff_is_explicit_and_history_append_only(self):
  t=self.db.create_task("Write then publish","book");self.offices.assign_task(t,"author",assigned_by="test",reason="draft");self.offices.handoff_task(t,from_role="author",to_role="press",reason="draft complete");self.assertEqual(self.offices.get_assignment(t)["owner_role"],"press");ev=self.offices.list_handoffs(t)
  with self.assertRaises(sqlite3.DatabaseError):self.db._connection().execute("UPDATE task_office_handoff_events SET reason='x' WHERE event_id=?",(ev[0]["event_id"],))
  self.db._connection().rollback()
 def test_assignment_rolls_back_when_handoff_event_insert_fails(self):
  t=self.db.create_task("Atomic assignment","audit");c=self.db._connection();c.execute("""CREATE TRIGGER fail_handoff_event BEFORE INSERT ON task_office_handoff_events BEGIN SELECT RAISE(ABORT,'injected handoff event failure'); END""");c.commit()
  try:
   with self.assertRaises(sqlite3.DatabaseError):self.offices.assign_task(t,"author",assigned_by="test",reason="atomicity")
   self.assertIsNone(self.offices.get_assignment(t))
  finally:
   c.execute("DROP TRIGGER fail_handoff_event");c.commit()
 def test_handoff_rolls_back_when_lineage_insert_fails(self):
  t=self.db.create_task("Atomic handoff","audit");self.offices.assign_task(t,"author",assigned_by="test",reason="draft");c=self.db._connection();c.execute("""CREATE TRIGGER fail_handoff_event_2 BEFORE INSERT ON task_office_handoff_events BEGIN SELECT RAISE(ABORT,'injected handoff event failure'); END""");c.commit()
  try:
   with self.assertRaises(sqlite3.DatabaseError):self.offices.handoff_task(t,from_role="author",to_role="press",reason="publish")
   a=self.offices.get_assignment(t);self.assertEqual(a["owner_role"],"author");self.assertEqual(a["handoff_count"],0);self.assertEqual(len(self.offices.list_handoffs(t)),1)
  finally:
   c.execute("DROP TRIGGER fail_handoff_event_2");c.commit()
 def test_worker_state_rolls_back_when_runtime_event_insert_fails(self):
  c=self.db._connection();before={r["role"]:r for r in self.offices.get_office_states()}["author"];c.execute("""CREATE TRIGGER fail_office_event BEFORE INSERT ON office_runtime_events BEGIN SELECT RAISE(ABORT,'injected office event failure'); END""");c.commit()
  try:
   with self.assertRaises(sqlite3.DatabaseError):self.offices.worker_started("author","worker-a",now_iso="2026-09-18T18:30:00+00:00")
   after={r["role"]:r for r in self.offices.get_office_states()}["author"];self.assertEqual(after["health_state"],before["health_state"]);self.assertEqual(after["current_worker_id"],before["current_worker_id"]);self.assertEqual(after["generation"],before["generation"])
  finally:
   c.execute("DROP TRIGGER fail_office_event");c.commit()
 def test_trigger_work_inherits_owner(self):
  tr=TaskTriggerCoordinator(self.db);tr.create_event_trigger(owner_role="research",source="unit",event_type="new",goal_template="Research {event_id}",project="r",valid_from="2026-09-17T00:00:00+00:00",review_by="2026-09-19T00:00:00+00:00",trigger_id="s2");e=tr.ingest_event(source="unit",event_type="new",dedupe_key="one",occurred_at="2026-09-17T12:00:00+00:00",received_at="2026-09-17T12:00:00+00:00",payload={});t=tr.fire_event(e.event_id,now_iso="2026-09-17T12:00:01+00:00")[0];self.offices.ensure_trigger_assignments(now_iso="2026-09-17T12:00:02+00:00");self.assertEqual(self.offices.get_assignment(t)["owner_role"],"research")
 def test_new_untriggered_enters_orchestra(self):
  t=self.db.create_task("Build","company");self.assertEqual(self.offices.assign_new_unowned_to_orchestra(),1);self.assertEqual(self.offices.get_assignment(t)["owner_role"],"orchestra")
 def test_office_worker_waits_for_durable_assignment_before_claim(self):
  t=self.db.create_task("Race-safe queue","company");c=DurableWorkerCoordinator(self.db);c.register_worker(role="orchestra",worker_id="ow");svc=PersistentWorkerService(db=self.db,coordinator=c,coordinator_factory=lambda:DurableWorkerCoordinator(CompanyDB(self.root/"state"/"company.sqlite")),config=WorkerServiceConfig(role="orchestra",lease_ttl_seconds=60,heartbeat_interval_seconds=10,use_office_assignments=True,triggered_only=False),worker_id="ow");now="2026-09-18T19:00:00+00:00";self.assertNotIn(t,svc.eligible_task_ids(now_iso=now));self.offices.assign_task(t,"orchestra",assigned_by="stillpointd",reason="durable queue ownership",now_iso=now);self.assertIn(t,svc.eligible_task_ids(now_iso=now))
 def test_worker_claims_assigned_queue_only(self):
  a=self.db.create_task("A","book");p=self.db.create_task("P","book");self.offices.assign_task(a,"author",assigned_by="t",reason="a");self.offices.assign_task(p,"press",assigned_by="t",reason="p");c=DurableWorkerCoordinator(self.db);c.register_worker(role="author",worker_id="aw");svc=PersistentWorkerService(db=self.db,coordinator=c,coordinator_factory=lambda:DurableWorkerCoordinator(CompanyDB(self.root/"state"/"company.sqlite")),config=WorkerServiceConfig(role="author",lease_ttl_seconds=60,heartbeat_interval_seconds=10,use_office_assignments=True,triggered_only=True),worker_id="aw");ids=svc.eligible_task_ids(now_iso="2026-09-17T12:00:00+00:00");self.assertIn(a,ids);self.assertNotIn(p,ids)
 def test_historical_failed_task_has_no_automatic_reentry(self):
  t=self.db.create_task("Old","legacy");self.db.update_task(t,status="failed",error="historical");self.offices.assign_task(t,"builder",assigned_by="t",reason="legacy");c=DurableWorkerCoordinator(self.db);c.register_worker(role="builder",worker_id="bw");svc=PersistentWorkerService(db=self.db,coordinator=c,coordinator_factory=lambda:DurableWorkerCoordinator(CompanyDB(self.root/"state"/"company.sqlite")),config=WorkerServiceConfig(role="builder",lease_ttl_seconds=60,heartbeat_interval_seconds=10,auto_retry_failed=True,use_office_assignments=True,triggered_only=True),worker_id="bw");self.assertNotIn(t,svc.eligible_task_ids(now_iso="2026-09-17T12:00:00+00:00"))
 def test_enqueue_is_durable_without_inline_execution(self):
  self.db.close();rt=runtime(self.root);t=rt.enqueue("Build async",project="company");row=rt.db.get_task(t);self.assertEqual(row["status"],"new");self.assertIsNone(row["plan_json"]);self.assertEqual(rt.db.list_runs(t),[]);rt.db.close();self.db=CompanyDB(self.root/"state"/"company.sqlite");self.offices=OfficeRuntimeCoordinator(self.db)
 def test_supervisor_control_plane_can_cross_constructor_serve_thread_boundary(self):
  self.db.close()
  sup=CompanySupervisor(SupervisorConfig(root=self.root,provider_name="mock",default_model="mock",supervisor_interval_seconds=.05,worker_poll_seconds=.02,lease_ttl_seconds=30,heartbeat_interval_seconds=5,retry_backoff_seconds=0,max_failures=2,start_office_workers=False))
  errors=[]
  def run():
   try: sup.serve()
   except Exception as exc: errors.append(exc)
  th=threading.Thread(target=run,daemon=True);th.start();time.sleep(.15);sup.stop_event.set();th.join(timeout=5)
  self.assertFalse(th.is_alive());self.assertEqual(errors,[]);self.assertIsNone(sup._lock_handle)
  self.db=CompanyDB(self.root/"state"/"company.sqlite");self.offices=OfficeRuntimeCoordinator(self.db)

 def test_supervisor_moves_queue_orchestra_to_builder_to_completion(self):
  self.db.close();rt=runtime(self.root);t=rt.enqueue("Build async",project="company");rt.db.close();sup=CompanySupervisor(SupervisorConfig(root=self.root,provider_name="mock",default_model="mock",supervisor_interval_seconds=.05,worker_poll_seconds=.02,lease_ttl_seconds=30,heartbeat_interval_seconds=5,retry_backoff_seconds=0,max_failures=2));th=threading.Thread(target=sup.serve,daemon=True);th.start();deadline=time.time()+5;status=None
  while time.time()<deadline:
   db=CompanyDB(self.root/"state"/"company.sqlite");status=(db.get_task(t) or {}).get("status");db.close()
   if status=="completed":break
   time.sleep(.05)
  sup.stop_event.set();th.join(timeout=5);self.assertEqual(status,"completed");self.db=CompanyDB(self.root/"state"/"company.sqlite");self.offices=OfficeRuntimeCoordinator(self.db);a=self.offices.get_assignment(t);self.assertEqual(a["owner_role"],"builder");self.assertEqual(a["state"],"released");ev=self.offices.list_handoffs(t);self.assertEqual(ev[0]["to_role"],"orchestra");self.assertTrue(any(x["event_type"]=="handoff" and x["to_role"]=="builder" for x in ev))
 def test_stage2_identity_and_kernel1_provenance(self):
  cp=json.loads((ROOT/"CHECKPOINT.json").read_text());mf=json.loads((ROOT/"RELEASE_MANIFEST.json").read_text());self.assertGreaterEqual(cp["schema_version"],20);self.assertEqual(cp["tests"]["v04_persistent_office_runtime"]["status"],"PASS");self.assertEqual(mf["provenance"]["canonical_v04_kernel1_merge"],"9f5ed7f3cc2f030648d997a38edb195f8c9b87bb");self.assertEqual(mf["provenance"]["canonical_v04_stage2_merge"],"0cee62189f39da747b9a506b6b2f4cc369bbacdc")
if __name__=="__main__":unittest.main()
