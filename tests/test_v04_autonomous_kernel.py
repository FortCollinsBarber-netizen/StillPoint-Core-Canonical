from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path

from stillpoint.db import CompanyDB
from stillpoint.supervisor import CompanySupervisor,SupervisorConfig,OFFICE_ROLES
from stillpoint.triggers import TaskTriggerCoordinator
from stillpoint.workers import DurableWorkerCoordinator
from stillpoint.worker_service import PersistentWorkerService,WorkerServiceConfig

ROOT=Path(__file__).resolve().parents[1]
T0=datetime(2026,9,17,22,30,0,tzinfo=timezone.utc)
T0S=T0.isoformat()

def _load_xai_probe():
    path=ROOT/"deploy"/"macos"/"probe_xai_access.py"
    spec=importlib.util.spec_from_file_location("v04_probe_xai_access",path)
    mod=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod

class V04AutonomousKernelTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.db=CompanyDB(self.root/"state"/"company.sqlite")
        self.triggers=TaskTriggerCoordinator(self.db)

    def tearDown(self):
        try:self.db.close()
        except Exception:pass
        self.tmp.cleanup()

    def _triggered_task(self,role="research",source="unit"):
        trig=self.triggers.create_event_trigger(
            owner_role=role,source=source,event_type="message_received",
            goal_template="Handle {event_id}",project="v04",
            valid_from=(T0-timedelta(hours=1)).isoformat(),
            review_by=(T0+timedelta(days=1)).isoformat(),
            trigger_id=f"trigger-{role}-{source}",
        )
        event=self.triggers.ingest_event(
            source=source,event_type="message_received",dedupe_key=f"{role}-{source}",
            occurred_at=T0S,received_at=T0S,payload={"ok":True},
        )
        return self.triggers.fire_event(event.event_id,now_iso=T0S)[0]

    def _service(self,task_id,role="research",**cfg):
        coord=DurableWorkerCoordinator(self.db)
        wid=f"worker-{role}"
        coord.register_worker(role=role,worker_id=wid,now_iso=T0S)
        db_path=self.root/"state"/"company.sqlite"
        return PersistentWorkerService(
            db=self.db,coordinator=coord,
            coordinator_factory=lambda: DurableWorkerCoordinator(CompanyDB(db_path)),
            config=WorkerServiceConfig(
                role=role,lease_ttl_seconds=60,heartbeat_interval_seconds=10,
                retry_backoff_seconds=cfg.get("retry_backoff_seconds",30),
                max_failures=cfg.get("max_failures",3),
                auto_retry_failed=cfg.get("auto_retry_failed",True),
                triggered_only=cfg.get("triggered_only",True),
                excluded_trigger_sources=cfg.get("excluded_trigger_sources",()),
            ),
            worker_id=wid,
        )

    def test_executor_exception_durably_fails_new_task(self):
        task=self._triggered_task()
        service=self._service(task)
        with self.assertRaisesRegex(RuntimeError,"boom"):
            service.run_once(lambda *_: (_ for _ in ()).throw(RuntimeError("boom")),now_iso=T0S)
        row=self.db.get_task(task)
        self.assertEqual(row["status"],"failed")
        retry=self.db._connection().execute(
            "SELECT * FROM worker_task_retry_state WHERE task_id=?",(task,)
        ).fetchone()
        self.assertEqual(int(retry["failure_count"]),1)

    def test_exhausted_retry_state_blocks_stale_new_task(self):
        task=self._triggered_task()
        service=self._service(task,max_failures=1,retry_backoff_seconds=0)
        service._set_retry(task,outcome="failed",now=T0,error="boom")
        self.db._connection().execute("UPDATE tasks SET status='new' WHERE id=?",(task,))
        self.db._connection().commit()
        self.assertNotIn(task,service.eligible_task_ids(now_iso=T0S))

    def test_retry_backoff_is_enforced_before_reclaim(self):
        task=self._triggered_task()
        service=self._service(task,max_failures=3,retry_backoff_seconds=30)
        service._set_retry(task,outcome="failed",now=T0,error="boom")
        self.assertNotIn(task,service.eligible_task_ids(now_iso=(T0+timedelta(seconds=20)).isoformat()))
        self.assertIn(task,service.eligible_task_ids(now_iso=(T0+timedelta(seconds=31)).isoformat()))

    def test_generic_signal_worker_cannot_claim_specialized_mailbox_event(self):
        task=self._triggered_task(role="signal",source="icloud")
        service=self._service(task,role="signal",excluded_trigger_sources=("icloud","gmail"))
        self.assertNotIn(task,service.eligible_task_ids(now_iso=T0S))

    def test_supervisor_fires_due_schedule_and_repairs_exhausted_state(self):
        trig=self.triggers.create_interval_trigger(
            owner_role="research",goal_template="Scheduled research",project="v04",
            valid_from=(T0-timedelta(hours=1)).isoformat(),
            review_by=(T0+timedelta(days=1)).isoformat(),
            next_run_at=T0S,interval_seconds=60,trigger_id="sched-research",
        )
        task=self._triggered_task(role="research",source="repair")
        c=self.db._connection()
        c.execute(
            """INSERT INTO worker_task_retry_state
               (task_id,failure_count,next_eligible_at,last_outcome,exhausted,updated_at)
               VALUES(?,?,?,?,?,?)""",
            (task,3,None,"failed",1,T0S),
        )
        c.execute("UPDATE tasks SET status='new' WHERE id=?",(task,))
        c.commit()
        self.db.close()

        sup=CompanySupervisor(SupervisorConfig(root=self.root,start_office_workers=False))
        try:
            out=sup.tick(now_iso=T0S)
            self.assertEqual(out["repaired_exhausted_task_states_this_tick"],1)
            self.assertEqual(len(out["scheduled_tasks_fired_this_tick"]),1)
            self.assertEqual(sup.db.get_task(task)["status"],"failed")
        finally:
            sup.close()
        self.db=CompanyDB(self.root/"state"/"company.sqlite")

    def test_xai_activation_probe_uses_exact_model_without_exposing_key(self):
        probe=_load_xai_probe()
        seen={}
        class FakeProvider:
            def __init__(self,**kwargs):
                seen["init"]=kwargs
            def generate(self,**kwargs):
                seen["generate"]=kwargs
                return type("R",(),{"text":"OK"})()
        result=probe.probe("secret-value","grok-4.6",provider_factory=FakeProvider)
        self.assertEqual(result.text,"OK")
        self.assertEqual(seen["init"]["api_key"],"secret-value")
        self.assertEqual(seen["generate"]["model"],"grok-4.6")
        self.assertEqual(seen["generate"]["phase"],"provider_capability_probe")

    def test_company_installer_probes_provider_before_launchd_activation(self):
        text=(ROOT/"deploy"/"macos"/"install_company_host.sh").read_text()
        self.assertLess(text.index("probe_xai_access.py"),text.index("/bin/launchctl bootstrap"))

    def test_v04_identity_and_stillpointd_entrypoint(self):
        cp=json.loads((ROOT/"CHECKPOINT.json").read_text())
        mf=json.loads((ROOT/"RELEASE_MANIFEST.json").read_text())
        py=(ROOT/"pyproject.toml").read_text()
        self.assertEqual(cp["version"],"0.4.0a1")
        self.assertEqual(cp["program"],"0.4-autonomous-company-os")
        self.assertEqual(cp["last_completed_milestone"],"v0.4-autonomous-kernel-1")
        self.assertEqual(mf["version"],"0.4.0a1")
        self.assertEqual(mf["program"],"0.4-autonomous-company-os")
        self.assertEqual(mf["baseline_patch"],"041-icloud-auth-boundary-correction")
        self.assertIn('stillpointd = "stillpoint.supervisor_service:main"',py)
        self.assertEqual(tuple(OFFICE_ROLES),(
            "orchestra","author","press","signal","ledger","research","builder","stillpoint"
        ))

if __name__=="__main__":
    unittest.main()
