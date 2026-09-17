from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


class Patch038ProductionSQLiteLifecycleTests(unittest.TestCase):
    def test_production_sqlite_lifecycle_is_clean_in_fresh_interpreter(self):
        root = Path(__file__).resolve().parents[1]
        tool = root / "tools" / "audit_sqlite_resource_lifecycle.py"
        proc = subprocess.run(
            [sys.executable, "-X", "dev", str(tool)],
            cwd=root,
            text=True,
            capture_output=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn('"sqlite_resource_leaks": 0', proc.stdout)
        self.assertIn('"network_actions_invoked": false', proc.stdout.lower())


if __name__ == "__main__":
    unittest.main()
