from __future__ import annotations
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from stillpoint.db import CompanyDB
from stillpoint.signal_mail_governance_policy import SignalMailGovernanceProvisioner, build_bootstrap_plan
from stillpoint.signal_mail_service import SignalMailboxServiceConfig, readiness

NOW=datetime(2026,9,18,12,0,tzinfo=timezone.utc)
APPROVED="abbada7549a95510d9552441a4f7bb1c92977f899cdfa953e8e394b058d00cc9"

class Patch038ProductionHostTests(unittest.TestCase):
    def setUp(self):
        self.td=tempfile.TemporaryDirectory()
        self.root=Path(self.td.name)
        fixture=Path(__file__).parent/"fixtures"/"signal_icloud_personal_business.draft.json"
        self.draft=json.loads(fixture.read_text())
        plan=build_bootstrap_plan(self.draft)
        self.assertEqual(plan.governance_sha256,APPROVED)
        self.facts=self.root/"state"/"signal_icloud_personal_business.facts.json"
        with CompanyDB(self.root/"state"/"company.sqlite") as db:
            p=SignalMailGovernanceProvisioner(db)
            p.seed(self.draft,expected_draft_sha256=plan.draft_sha256,ceo_confirmed=True)
            p.apply(plan.governance_spec,facts_file=self.facts,expected_sha256=APPROVED,ceo_confirmed=True)

    def tearDown(self):
        self.td.cleanup()

    def config(self):
        return SignalMailboxServiceConfig.from_env({
            "STILLPOINT_ROOT":str(self.root),
            "STILLPOINT_MAIL_PROVIDER":"icloud",
            "STILLPOINT_MAIL_ACCOUNT":"fortcollinsbarber@icloud.com",
            "STILLPOINT_MAIL_JURISDICTION":"personal_business",
            "STILLPOINT_ICLOUD_APP_PASSWORD":"test-app-specific-secret",
            "STILLPOINT_SIGNAL_DELEGATION_ID":"signal-delegation-icloud-personal-business-v1",
            "STILLPOINT_SIGNAL_MAIL_TRIGGER_ID":"signal-trigger-icloud-personal-business-v1",
            "STILLPOINT_SIGNAL_GOVERNANCE_SHA256":APPROVED,
            "STILLPOINT_SIGNAL_FACTS_FILE":str(self.facts),
            "STILLPOINT_PROVIDER":"mock",
            "STILLPOINT_SIGNAL_ALLOW_MOCK":"1",
        })

    def test_provider_neutral_readiness_is_side_effect_free_and_exact(self):
        c=self.config()
        r=readiness(c,now_fn=lambda:NOW)
        self.assertTrue(r["ready"],r)
        self.assertEqual(r["governance_sha256"],APPROVED)
        self.assertEqual(r["mailbox"]["provider"],"icloud")
        self.assertNotIn("test-app-specific-secret",json.dumps(r))

    def test_wrong_governance_digest_fails_closed(self):
        c=self.config()
        bad=type(c)(**{**c.__dict__,"governance_sha256":"0"*64})
        r=readiness(bad,now_fn=lambda:NOW)
        self.assertFalse(r["ready"])
        self.assertIn("digest",r["error"].lower())

    def test_review_boundary_fails_closed(self):
        c=self.config()
        r=readiness(c,now_fn=lambda:datetime(2026,10,17,20,0,tzinfo=timezone.utc))
        self.assertFalse(r["ready"])

    def test_release_metadata_declares_nonroot_keychain_launchagent(self):
        root=Path(__file__).resolve().parents[1]
        m=json.loads((root/"RELEASE_MANIFEST.json").read_text())
        h=m["host_runtime"]
        self.assertEqual(h["service_scope"],"per-user LaunchAgent")
        self.assertEqual(h["secret_store"],"macOS Keychain")
        self.assertFalse(h["runs_as_root"])
        self.assertFalse(h["production_activation"])

    def test_deployment_assets_contain_no_secret_values(self):
        root=Path(__file__).resolve().parents[1]
        text="\n".join(p.read_text() for p in (root/"deploy"/"macos").iterdir() if p.is_file())
        self.assertIn("STILLPOINT_ICLOUD_APP_PASSWORD",text)
        self.assertIn("XAI_API_KEY",text)
        self.assertNotIn("test-app-specific-secret",text)

if __name__=="__main__":
    unittest.main()
