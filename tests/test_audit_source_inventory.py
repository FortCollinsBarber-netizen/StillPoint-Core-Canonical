"""Offline contract checks for the source inventory helper."""
import importlib.util
import tempfile
import unittest
import subprocess
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "audit_source_inventory.py"
spec = importlib.util.spec_from_file_location("audit_source_inventory", MODULE_PATH)
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)


class InventoryTests(unittest.TestCase):
    def test_tracked_only_and_physical_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "example.py").write_text("# TODO: document\nprint('ok')", encoding="utf-8")
            (root / "notes.txt").write_text("reference\n", encoding="utf-8")
            (root / "ignore.py").write_text("not tracked", encoding="utf-8")
            (root / "binary.dat").write_bytes(b"A\x00B")
            subprocess.run(["git", "-C", str(root), "add", "example.py", "notes.txt", "binary.dat"], check=True)
            report = audit_module.inventory(root)
            self.assertEqual(report["tracked_file_count"], 3)
            self.assertEqual(report["code_or_config_count"], 1)
            rows = {x["path"]: x for x in report["files"]}
            self.assertNotIn("ignore.py", rows)
            self.assertEqual(rows["example.py"]["physical_lines"], 2)
            self.assertEqual(rows["example.py"]["review_markers"], 1)
            self.assertEqual(rows["binary.dat"]["kind"], "binary_or_non_utf8")
            self.assertIsNone(rows["binary.dat"]["physical_lines"])
            self.assertTrue(all(x["review_status"] == "NOT_READ" for x in rows.values()))

    def test_missing_worktree_file_is_not_claimed_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "vanished.swift").write_text("let a = 1\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "vanished.swift"], check=True)
            (root / "vanished.swift").unlink()
            row = audit_module.inventory(root)["files"][0]
            self.assertEqual(row["kind"], "missing_worktree_file")
            self.assertIsNone(row["sha256"])


if __name__ == "__main__":
    unittest.main()
