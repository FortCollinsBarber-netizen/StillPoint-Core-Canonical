"""Bounded Unix default permissions for StillPoint's per-user macOS launchers."""
from __future__ import annotations

import os
import sqlite3
import stat
import tempfile
import unittest
from contextlib import closing
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = (
    "deploy/macos/install_company_host.sh",
    "deploy/macos/run_company.sh",
    "deploy/macos/install_signal_host.sh",
    "deploy/macos/run_signal_mail.sh",
)


class MacOSRuntimeFileModeTests(unittest.TestCase):
    def test_per_user_launchers_set_private_umask_before_io(self):
        for path in SCRIPTS:
            with self.subTest(path=path):
                data = (ROOT / path).read_text(encoding="utf-8").splitlines()
                first_five = "\n".join(data[:8])
                self.assertIn("set -euo pipefail", first_five)
                self.assertIn("umask 077", first_five)
                self.assertLess(
                    first_five.index("umask 077"),
                    len(first_five),
                )

    def test_new_sqlite_file_is_owner_only_under_launcher_umask(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "company.sqlite"
            old = os.umask(0o077)
            try:
                with closing(sqlite3.connect(target)) as db, db:
                    db.execute("CREATE TABLE probe (id INTEGER PRIMARY KEY)")
            finally:
                os.umask(old)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
