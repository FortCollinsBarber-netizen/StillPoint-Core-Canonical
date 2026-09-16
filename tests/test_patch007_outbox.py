from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from stillpoint.adapters.outbox import BoundedOutboxAdapter, OutboxBoundaryError
from stillpoint.adapters.production import (
    build_production_registry,
    configured_outbox_root,
    inspect_production_adapters,
)
from stillpoint.adapters.registry import ActionAdapterRegistry
from stillpoint.contracts.models import ArtifactRef
from stillpoint.db import CompanyDB
from stillpoint.registry import AgentRegistry
from stillpoint.runtime import CompanyRuntime
from stillpoint.authority.deterministic import assess_bundle
from stillpoint.temporal.action_gate import action_domain


ROOT=Path(__file__).resolve().parents[1]


class MockProvider:
    default_model="mock"
    def generate(self, **kwargs):
        return type("R", (), {
            "text":"PATCH007 ARTIFACT BODY",
            "citations":[],
            "provider_response_id":"mock",
            "usage":{},
            "model":"mock",
        })()


class Patch007OutboxTests(unittest.TestCase):
    def make(self,tmp):
        return CompanyRuntime(
            root=tmp,
            db=CompanyDB(tmp/"state"/"company.sqlite"),
            registry=AgentRegistry(ROOT/"config"/"agents.json"),
            provider=MockProvider(),
            default_model="mock",
            smart_routing=False,
        )

    def approved_export(self,rt,outbox):
        with patch.dict(os.environ,{"STILLPOINT_OUTBOX_ROOT":str(outbox)},clear=True):
            out=rt.submit("Export this artifact to the production outbox.")
            self.assertEqual(out.status.value,"waiting_approval")
            action=rt.db.list_action_requests(out.task_id)[0]
            self.assertEqual(action["action_type"],"export_artifact")
            rt.approve(out.task_id)
            return out.task_id,rt.db.get_action_request(action["id"])

    def test_export_does_not_downgrade_higher_impact_actions(self):
        self.assertEqual(
            assess_bundle("Send this export to the publisher.").primary_intent,
            "send_email",
        )
        self.assertEqual(
            assess_bundle("Publish this export to Amazon.").primary_intent,
            "publish",
        )
        self.assertEqual(
            assess_bundle("Export this artifact to the production outbox.").primary_intent,
            "export_artifact",
        )

    def test_export_has_mandatory_temporal_authority_domain(self):
        self.assertEqual(action_domain("export_artifact"), "operational")

    def test_explicit_action_binds_root_before_approval(self):
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d);outbox=tmp/"out";rt=self.make(tmp/"runtime")
            with patch.dict(os.environ,{"STILLPOINT_OUTBOX_ROOT":str(outbox)},clear=True):
                out=rt.submit("Export this artifact to the production outbox.")
            action=rt.db.list_action_requests(out.task_id)[0]
            root=str(outbox.resolve(strict=False))
            self.assertEqual(action["target"],"bounded_outbox:"+root)
            self.assertIn("outbox_root="+root,json.loads(action["scope_json"]))
            self.assertEqual(json.loads(action["success_criteria_json"]),["export_receipt"])
            self.assertEqual(len(json.loads(action["artifact_refs_json"])),1)
            rt.db.close()

    def test_export_requires_root_at_action_creation(self):
        with tempfile.TemporaryDirectory() as d:
            rt=self.make(Path(d))
            with patch.dict(os.environ,{},clear=True):
                with self.assertRaises(Exception):
                    rt.submit("Export this artifact to the production outbox.")
            rt.db.close()

    def test_production_registry_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d);rt=self.make(tmp/"runtime")
            with patch.dict(os.environ,{"STILLPOINT_OUTBOX_ROOT":str(tmp/"out")},clear=True):
                status=inspect_production_adapters()
                self.assertTrue(status["ok"])
                self.assertEqual(status["enabled"],[])
                self.assertEqual(build_production_registry(rt)._adapters,[])
            rt.db.close()

    def test_enable_requires_explicit_root(self):
        with patch.dict(os.environ,{"STILLPOINT_ENABLE_OUTBOX":"1"},clear=True):
            self.assertFalse(inspect_production_adapters()["ok"])

    def test_default_off_registry_cannot_resolve_real_outbox(self):
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d);outbox=tmp/"out";rt=self.make(tmp/"runtime")
            _,action=self.approved_export(rt,outbox)
            req=rt._request_from_row(action)
            with patch.dict(os.environ,{"STILLPOINT_OUTBOX_ROOT":str(outbox)},clear=True):
                reg=build_production_registry(rt)
                self.assertEqual(reg.resolve(req).name,"null")
            rt.db.close()

    def test_end_to_end_export_completes_with_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d);outbox=tmp/"out";rt=self.make(tmp/"runtime")
            task_id,action=self.approved_export(rt,outbox)
            adapter=BoundedOutboxAdapter(db=rt.db,outbox_root=outbox,enabled=True)
            result=rt.execute_action(action["id"],ActionAdapterRegistry([adapter]))
            self.assertEqual(result["status"],"completed")
            self.assertEqual(result["result"].adapter,"bounded_outbox")
            self.assertEqual(result["result"].evidence[0].type,"export_receipt")
            action_dir=outbox/action["id"]
            receipt=json.loads((action_dir/"_receipt.json").read_text())
            self.assertEqual(receipt["action_id"],action["id"])
            self.assertEqual(
                receipt["warrant_id"],
                rt.db.get_action_request(action["id"])["warrant_id"],
            )
            exported=action_dir/receipt["artifact"]["name"]
            self.assertEqual(exported.read_text(),"PATCH007 ARTIFACT BODY")
            self.assertEqual(
                hashlib.sha256(exported.read_bytes()).hexdigest(),
                receipt["artifact"]["sha256"],
            )
            self.assertEqual(rt.db.get_task(task_id)["status"],"completed")
            with self.assertRaises(Exception):
                rt.execute_action(action["id"],ActionAdapterRegistry([adapter]))
            rt.db.close()

    def test_root_change_after_approval_cannot_redirect_effect(self):
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d);rt=self.make(tmp/"runtime")
            _,action=self.approved_export(rt,tmp/"authorized")
            req=rt._request_from_row(action)
            wrong=BoundedOutboxAdapter(db=rt.db,outbox_root=tmp/"different",enabled=True)
            self.assertFalse(wrong.can_execute(req))
            with self.assertRaises(OutboxBoundaryError):
                wrong.execute(req)
            self.assertFalse((tmp/"different"/action["id"]).exists())
            rt.db.close()

    def test_adapter_rejects_unsafe_artifact_name(self):
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d);outbox=tmp/"out";rt=self.make(tmp/"runtime")
            _,action=self.approved_export(rt,outbox)
            req=rt._request_from_row(action)
            ref=req.artifact_refs[0]
            req.artifact_refs=[ArtifactRef(
                name="../escape.txt",
                sha256=ref.sha256,
                kind=ref.kind,
                artifact_id=ref.artifact_id,
                version=ref.version,
            )]
            adapter=BoundedOutboxAdapter(db=rt.db,outbox_root=outbox,enabled=True)
            self.assertFalse(adapter.can_execute(req))
            with self.assertRaises(OutboxBoundaryError):
                adapter.execute(req)
            self.assertFalse((tmp/"escape.txt").exists())
            rt.db.close()

    def test_symlink_root_rejected(self):
        if not hasattr(os,"symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d);real=tmp/"real";real.mkdir();link=tmp/"link"
            try:
                link.symlink_to(real,target_is_directory=True)
            except OSError:
                self.skipTest("symlink not permitted")
            rt=self.make(tmp/"runtime")
            with self.assertRaises(OutboxBoundaryError):
                BoundedOutboxAdapter(db=rt.db,outbox_root=link,enabled=True)
            with patch.dict(os.environ,{"STILLPOINT_OUTBOX_ROOT":str(link)},clear=True):
                with self.assertRaises(Exception):
                    configured_outbox_root()
            rt.db.close()

    def test_hash_tamper_fails_closed_before_effect(self):
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d);outbox=tmp/"out";rt=self.make(tmp/"runtime")
            _,action=self.approved_export(rt,outbox)
            ref=json.loads(action["artifact_refs_json"])[0]
            conn=rt.db._connection()
            conn.execute(
                "UPDATE agent_runs SET output='TAMPERED' "
                "WHERE id=(SELECT produced_by_run_id FROM artifacts WHERE id=?)",
                (ref["artifact_id"],),
            )
            conn.commit()
            adapter=BoundedOutboxAdapter(db=rt.db,outbox_root=outbox,enabled=True)
            req=rt._request_from_row(action)
            self.assertFalse(adapter.can_execute(req))
            self.assertFalse((outbox/action["id"]).exists())
            rt.db.close()

    def test_adapter_direct_idempotency_is_deterministic(self):
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d);outbox=tmp/"out";rt=self.make(tmp/"runtime")
            _,action=self.approved_export(rt,outbox)
            req=rt._request_from_row(action)
            adapter=BoundedOutboxAdapter(db=rt.db,outbox_root=outbox,enabled=True)
            first=adapter.execute(req);second=adapter.execute(req)
            self.assertEqual(first.external_id,second.external_id)
            self.assertEqual(first.evidence[0].sha256,second.evidence[0].sha256)
            rt.db.close()

    def test_preexisting_destination_without_receipt_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d);outbox=tmp/"out";rt=self.make(tmp/"runtime")
            _,action=self.approved_export(rt,outbox)
            req=rt._request_from_row(action);ref=req.artifact_refs[0]
            action_dir=outbox/req.action_id;action_dir.mkdir(parents=True)
            (action_dir/ref.name).write_text("PATCH007 ARTIFACT BODY")
            adapter=BoundedOutboxAdapter(db=rt.db,outbox_root=outbox,enabled=True)
            with self.assertRaises(OutboxBoundaryError):
                adapter.execute(req)
            self.assertFalse((action_dir/"_receipt.json").exists())
            rt.db.close()

    def test_post_effect_failure_becomes_uncertain_no_auto_retry(self):
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d);outbox=tmp/"out";rt=self.make(tmp/"runtime")
            _,action=self.approved_export(rt,outbox)
            inner=BoundedOutboxAdapter(db=rt.db,outbox_root=outbox,enabled=True)
            class CrashAfterEffect:
                name="crash_after_outbox"
                action_types=("export_artifact",)
                def can_execute(self,request): return inner.can_execute(request)
                def execute(self,request):
                    inner.execute(request)
                    raise RuntimeError("simulated crash after effect")
            with self.assertRaises(RuntimeError):
                rt.execute_action(
                    action["id"],ActionAdapterRegistry([CrashAfterEffect()])
                )
            dispatch=rt.db.get_action_dispatch(action["id"])
            self.assertEqual(dispatch["state"],"uncertain")
            self.assertTrue((outbox/action["id"]).is_dir())
            with self.assertRaises(RuntimeError):
                rt.execute_action(
                    action["id"],ActionAdapterRegistry([inner])
                )
            rec=rt.reconcile_action_dispatch(
                action["id"],effect_occurred=True,note="verified bounded outbox effect"
            )
            self.assertEqual(rec["state"],"reconciled_effect")
            with self.assertRaises(RuntimeError):
                rt.execute_action(
                    action["id"],ActionAdapterRegistry([inner])
                )
            rt.db.close()


if __name__=="__main__":
    unittest.main()
