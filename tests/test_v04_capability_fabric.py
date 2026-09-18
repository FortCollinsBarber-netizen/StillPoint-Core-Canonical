from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from stillpoint.capabilities import code_execution, web_research
from stillpoint.capability_fabric import CapabilityBroker, capability_manifest_path
from stillpoint.db import CompanyDB
from stillpoint.providers.mock import MockProvider
from stillpoint.registry import AgentRegistry
from stillpoint.runtime import CompanyRuntime
from stillpoint.supervisor import CompanySupervisor, SupervisorConfig

ROOT=Path(__file__).resolve().parents[1]
STAGE2="0cee62189f39da747b9a506b6b2f4cc369bbacdc"


class CaptureProvider(MockProvider):
    def __init__(self):
        self.calls=[]
    def generate(self, *, system, prompt, model, tools=None, **kwargs):
        self.calls.append(list(tools or []))
        return super().generate(system=system,prompt=prompt,model=model,tools=tools,**kwargs)


class V04CapabilityFabricTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.db=CompanyDB(self.root/"state"/"company.sqlite")
        self.broker=CapabilityBroker(self.db,capability_manifest_path(self.root))
        self.broker.sync_manifest()

    def tearDown(self):
        try:self.db.close()
        except Exception:pass
        self.tmp.cleanup()

    def test_schema21_catalog_and_grants_exist(self):
        self.assertEqual(self.db.schema_version,21)
        snap=self.broker.snapshot(include_events=False)
        self.assertEqual({x["capability_id"] for x in snap["catalog"]},{"web_research","x_research","code_execution","structured_output"})
        self.assertTrue(snap["manifest_audit"]["ok"])
        self.assertFalse(any(bool(x["external_effect"]) for x in snap["catalog"]))

    def test_durable_grants_preserve_stage2_provider_tool_matrix(self):
        expected={
            "press":{"web_research"},
            "signal":{"web_research","x_research"},
            "ledger":{"web_research","code_execution"},
            "research":{"web_research","x_research"},
            "builder":{"web_research","code_execution"},
            "stillpoint":{"web_research"},
        }
        snap=self.broker.snapshot(include_events=False)
        actual={k:set(v) for k,v in snap["active_by_office"].items()}
        self.assertEqual(actual,expected)
        self.assertNotIn("author",actual)
        self.assertNotIn("orchestra",actual)

    def test_ungranted_capability_is_blocked_and_not_offered(self):
        out=self.broker.resolve_provider_requests(
            role="author",
            requests=[web_research()],
            declared_capabilities=["web_research"],
            task_id=None,
            phase="unit",
            provider="mock",
        )
        self.assertEqual(out,[])
        event=self.broker.list_events(limit=1)[0]
        self.assertEqual(event["event_type"],"blocked")
        self.assertEqual(event["detail"]["reason"],"office_grant_not_current")

    def test_manifest_sync_cannot_reactivate_revoked_grant(self):
        self.assertTrue(self.broker.is_granted("research","web_research"))
        self.broker.set_grant_status(
            "research","web_research","revoked",
            changed_by="test:ceo-policy",
            reason="regression proof",
        )
        self.assertFalse(self.broker.is_granted("research","web_research"))
        self.broker.sync_manifest()
        self.assertFalse(self.broker.is_granted("research","web_research"))

    def test_runtime_routes_real_provider_tool_offer_through_broker(self):
        self.db.close()
        provider=CaptureProvider()
        rt=CompanyRuntime(
            root=self.root,
            db=CompanyDB(self.root/"state"/"company.sqlite"),
            registry=AgentRegistry(ROOT/"config"/"agents.json"),
            provider=provider,
            default_model="mock",
            smart_routing=False,
            allowed_import_roots=[self.root],
        )
        try:
            out=rt.submit("Research the latest official sources about quantum error correction",project="capability-proof")
            self.assertEqual(out.plan.primary,"research")
            offered=[e for e in rt.capability_broker.list_events(limit=20) if e["event_type"]=="offered"]
            self.assertTrue(any(e["capability_id"]=="web_research" and e["role"]=="research" for e in offered))
            self.assertTrue(any(any(t.capability=="web_research" for t in call) for call in provider.calls))
            self.assertTrue(all(e["detail"]["external_authority_granted"] is False for e in offered))
            self.assertTrue(all(e["detail"]["tool_use_proven"] is False for e in offered))
        finally:
            rt.db.close()
            self.db=CompanyDB(self.root/"state"/"company.sqlite")
            self.broker=CapabilityBroker(self.db,capability_manifest_path(self.root))

    def test_capability_events_are_append_only(self):
        self.broker.resolve_provider_requests(
            role="builder",
            requests=[code_execution()],
            declared_capabilities=["code_execution"],
            task_id=None,
            phase="unit",
            provider="mock",
        )
        event=self.broker.list_events(limit=1)[0]
        with self.assertRaises(sqlite3.DatabaseError):
            self.db._connection().execute(
                "UPDATE capability_events SET event_type='blocked' WHERE event_id=?",
                (event["event_id"],),
            )
        self.db._connection().rollback()

    def test_stage3_identity_stage2_provenance_and_supervisor_surface(self):
        self.assertEqual((ROOT/"config"/"capabilities.json").read_bytes(),(ROOT/"stillpoint"/"defaults"/"capabilities.json").read_bytes())
        cp=json.loads((ROOT/"CHECKPOINT.json").read_text())
        mf=json.loads((ROOT/"RELEASE_MANIFEST.json").read_text())
        self.assertEqual(cp["version"],"0.4.0a3")
        self.assertEqual(cp["schema_version"],21)
        self.assertEqual(cp["last_completed_milestone"],"v0.4-capability-fabric-3")
        self.assertEqual(cp["git"]["v04_stage2_merge_commit"],STAGE2)
        self.assertEqual(mf["provenance"]["canonical_v04_stage2_merge"],STAGE2)
        self.db.close()
        sup=CompanySupervisor(SupervisorConfig(root=self.root,provider_name="mock",default_model="mock",start_office_workers=False))
        try:
            snap=sup.snapshot()
            self.assertTrue(snap["capability_fabric"]["manifest_audit"]["ok"])
            self.assertEqual(snap["capability_fabric"]["authority_semantics"],"capability grant != external-action authority")
        finally:
            sup.close()
            self.db=CompanyDB(self.root/"state"/"company.sqlite")
            self.broker=CapabilityBroker(self.db,capability_manifest_path(self.root))


if __name__=="__main__":
    unittest.main()
