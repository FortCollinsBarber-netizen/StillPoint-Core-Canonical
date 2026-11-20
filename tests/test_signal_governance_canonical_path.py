import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from stillpoint.db import CompanyDB
from stillpoint.signal_mail_governance_policy import (
    SignalMailGovernanceError,
    SignalMailGovernanceProvisioner,
    build_bootstrap_plan,
)
from stillpoint.signal_mail_service import SignalMailboxServiceConfig, readiness


class CanonicalCustodyPathTests(unittest.TestCase):
    def setUp(self):
        temp = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(temp).resolve() / "real"
        self.db = self.enterContext(CompanyDB(self.root / "state/company.sqlite"))
        fixture = Path(__file__).parent / "fixtures/signal_icloud_personal_business.draft.json"
        draft = json.loads(fixture.read_text(encoding="utf-8"))
        self.plan = build_bootstrap_plan(draft)
        self.provisioner = SignalMailGovernanceProvisioner(self.db)
        self.provisioner.seed(draft, expected_draft_sha256=self.plan.draft_sha256, ceo_confirmed=True)

    def apply(self, facts_file):
        return self.provisioner.apply(
            self.plan.governance_spec,
            facts_file=facts_file,
            expected_sha256=self.plan.governance_sha256,
            ceo_confirmed=True,
        )

    def test_symlinked_parent_preserves_verified_custody(self):
        alias = self.root.parent / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        facts = alias / "facts/snapshot.json"
        canonical = self.root / "facts/snapshot.json"

        result = self.apply(facts)
        self.assertEqual(result["facts_file"], str(canonical))

        spec = self.plan.governance_spec
        config = SignalMailboxServiceConfig.from_env({
            "STILLPOINT_ROOT": str(self.root),
            "STILLPOINT_MAIL_PROVIDER": spec.identity.provider,
            "STILLPOINT_MAIL_ACCOUNT": spec.identity.account,
            "STILLPOINT_MAIL_JURISDICTION": spec.identity.jurisdiction,
            "STILLPOINT_ICLOUD_APP_PASSWORD": "test-only-secret",
            "STILLPOINT_SIGNAL_DELEGATION_ID": spec.delegation_id,
            "STILLPOINT_SIGNAL_MAIL_TRIGGER_ID": spec.trigger_id,
            "STILLPOINT_SIGNAL_GOVERNANCE_SHA256": self.plan.governance_sha256,
            "STILLPOINT_SIGNAL_FACTS_FILE": str(facts),
            "STILLPOINT_PROVIDER": "mock",
            "STILLPOINT_SIGNAL_ALLOW_MOCK": "1",
        })
        status = readiness(config, now_fn=lambda: datetime(2026, 9, 18, 12, tzinfo=timezone.utc))
        self.assertTrue(status["ready"], status)

        replay = self.apply(canonical)
        self.assertTrue(replay["reused_existing"])
        rows = self.db._connection().execute(
            "SELECT facts_path, status FROM signal_governance_materializations WHERE governance_sha256=?",
            (self.plan.governance_sha256,),
        ).fetchall()
        self.assertEqual([tuple(row) for row in rows], [(str(canonical), "materialized")])

    def test_final_symlink_is_rejected_before_materialization(self):
        target = self.root / "target.json"
        target.write_text("untouched", encoding="utf-8")
        facts = self.root / "snapshot.json"
        facts.symlink_to(target)

        with self.assertRaisesRegex(SignalMailGovernanceError, "not a symlink"):
            self.apply(facts)

        self.assertTrue(facts.is_symlink())
        self.assertEqual(target.read_text(encoding="utf-8"), "untouched")
        rows = self.db._connection().execute("SELECT 1 FROM signal_governance_materializations").fetchall()
        self.assertEqual(rows, [])
