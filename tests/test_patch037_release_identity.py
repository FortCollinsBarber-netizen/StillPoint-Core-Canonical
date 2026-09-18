from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CP=json.loads((ROOT/"CHECKPOINT.json").read_text())
MF=json.loads((ROOT/"RELEASE_MANIFEST.json").read_text())

class Patch037ReleaseIdentityTests(unittest.TestCase):
    def test_schema_and_migration_identity_are_current(self):
        migration_files=sorted(
            path for path in (ROOT/"migrations").glob("[0-9][0-9][0-9]_*.sql")
        )
        self.assertTrue(migration_files)
        expected_names=[path.name for path in migration_files]
        latest=int(expected_names[-1].split("_",1)[0])

        # Release metadata follows the actual earned migration set rather than
        # freezing an old schema number as permanent identity.
        self.assertEqual(CP["schema_version"],latest)
        self.assertEqual(MF["schema_version"],latest)
        self.assertEqual(CP["migrations"],expected_names)

        packaged=ROOT/"stillpoint"/"migrations"
        for source in migration_files:
            mirror=packaged/source.name
            self.assertTrue(mirror.is_file(),source.name)
            self.assertEqual(source.read_bytes(),mirror.read_bytes(),source.name)

    def test_release_metadata_does_not_activate_production(self):
        self.assertEqual(CP["external_action_adapters"]["production_enabled"],[])
        self.assertEqual(CP["production_services"]["auto_started"],[])
        self.assertFalse(CP["release_candidate"]["production_activation"])
        self.assertFalse(MF["signal"]["production_activation"])
        self.assertFalse(MF["release_invariants"]["credentials_committed"])

    def test_apple_first_signal_identity_is_exact(self):
        s=MF["signal"]
        self.assertEqual(s["provider"],"icloud")
        self.assertEqual(s["account"],"fortcollinsbarber@icloud.com")
        self.assertEqual(s["jurisdiction"],"personal_business")
        self.assertEqual(s["autonomous_classes"],["scheduling","acknowledgement","routine_information"])
        self.assertEqual(s["mandatory_review_days"],30)

    def test_governance_digest_matches_checkpoint_and_manifest(self):
        digest="abbada7549a95510d9552441a4f7bb1c92977f899cdfa953e8e394b058d00cc9"
        self.assertEqual(CP["signal_governance"]["policy_digest_sha256"],digest)
        self.assertEqual(MF["signal"]["governance_policy_digest_sha256"],digest)
        self.assertFalse(MF["signal"]["approval_evidence_committed"])

if __name__=="__main__":unittest.main()
