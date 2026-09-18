from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from stillpoint.doctor import _migration_versions, _mirror_check

ROOT=Path(__file__).resolve().parents[1]


class ReleaseHardeningTests(unittest.TestCase):
    def test_migration_versions_are_numeric_and_ordered(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/"001_a.sql").write_text("-- a")
            (root/"003_c.sql").write_text("-- c")
            (root/"ignore.txt").write_text("x")
            self.assertEqual(_migration_versions(root),[1,3])

    def test_migration_mirror_detects_filename_drift(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            a=root/"a"; b=root/"b"; a.mkdir(); b.mkdir()
            (a/"001_a.sql").write_text("-- a")
            (b/"001_other.sql").write_text("-- a")
            result=_mirror_check(a,b)
            self.assertFalse(result["ok"])

    def test_migration_mirror_detects_content_drift(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            a=root/"a"; b=root/"b"; a.mkdir(); b.mkdir()
            (a/"001_a.sql").write_text("-- a")
            (b/"001_a.sql").write_text("-- b")
            result=_mirror_check(a,b)
            self.assertFalse(result["ok"])
            self.assertEqual(result["mismatches"],["001_a.sql"])

    def test_company_and_signal_use_distinct_atomic_release_pointers(self):
        company=(ROOT/"deploy/macos/install_company_host.sh").read_text()
        signal=(ROOT/"deploy/macos/install_signal_host.sh").read_text()
        company_run=(ROOT/"deploy/macos/run_company.sh").read_text()
        signal_run=(ROOT/"deploy/macos/run_signal_mail.sh").read_text()

        self.assertIn('RELEASES="$APP/releases"',company)
        self.assertIn('CURRENT="$APP/current-company"',company)
        self.assertIn('RELEASE="$RELEASES/$COMMIT"',company)
        self.assertIn('os.replace(tmp,current)',company)
        self.assertIn('chmod -R a-w "$RELEASE"',company)

        self.assertIn('RELEASES="$APP_SUPPORT/releases"',signal)
        self.assertIn('CURRENT="$APP_SUPPORT/current-signal"',signal)
        self.assertIn('RELEASE="$RELEASES/$COMMIT"',signal)
        self.assertIn('os.replace(tmp,current)',signal)
        self.assertIn('chmod -R a-w "$RELEASE"',signal)

        self.assertIn('$APP/current-company',company_run)
        self.assertIn('$APP_SUPPORT/current-signal',signal_run)
        self.assertNotEqual("current-company","current-signal")

    def test_installers_never_replace_a_live_shared_venv_or_core_checkout(self):
        for name in ("install_company_host.sh","install_signal_host.sh"):
            script=(ROOT/"deploy/macos"/name).read_text()
            self.assertNotIn('rm -rf "$VENV"',script)
            self.assertNotIn('reset --hard origin/main',script)
            self.assertNotIn('="$APP/venv"',script)
            self.assertNotIn('="$APP_SUPPORT/venv"',script)
            self.assertNotIn('="$APP/Core"',script)
            self.assertNotIn('="$APP_SUPPORT/Core"',script)

    def test_signal_installer_is_not_bound_to_stale_patch_041_identity(self):
        script=(ROOT/"deploy/macos/install_signal_host.sh").read_text()
        self.assertNotIn("041-icloud-auth-boundary-correction",script)
        self.assertIn('gh api "repos/$REPO/commits/main"',script)
        self.assertIn('canonical CI is not green',script)


if __name__=="__main__":
    unittest.main()
