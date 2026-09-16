from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from stillpoint.doctor import _migration_versions, _mirror_check


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


if __name__=="__main__":
    unittest.main()
