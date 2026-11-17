"""Tests for the browser export using ONLY the already-public canonical Core.

A partial test build uses 2026, 2027, and 2075 for speed. A production export
must contain all 50 years and explicitly announces that fact in its manifest.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools.export_public_calendar_site import export_site
from stillpoint.calendar_core.runtime_surface import calendar_day_payload


class PublicCalendarSiteExportTests(unittest.TestCase):
    def test_bounded_core_generated_shards_and_year_transition(self):
        with tempfile.TemporaryDirectory(prefix="stillpoint-browser-test-") as td:
            root = Path(td)
            manifest = export_site(root, years=[2026, 2027, 2075])
            self.assertEqual(manifest["schema"], "stillpoint.public-calendar-static.v1")
            self.assertFalse(manifest["complete_publication"])
            self.assertEqual(manifest["first_common_year"], 2026)
            self.assertEqual(manifest["last_common_year"], 2075)
            self.assertTrue(manifest["no_2076_publication"])
            self.assertEqual(len(manifest["years"]), 3)
            self.assertTrue((root / "index.html").is_file())
            self.assertEqual(
                json.loads((root / "data" / "index.json").read_text()),
                manifest,
            )

            year_files = {}
            for entry in manifest["years"]:
                blob = (root / entry["path"]).read_bytes()
                self.assertEqual(hashlib.sha256(blob).hexdigest(), entry["sha256"])
                data = json.loads(blob)
                self.assertEqual(data["year"], entry["year"])
                self.assertEqual(data["publication_digest"], manifest["publication_digest"])
                self.assertEqual(len(data["days"]), 364)
                self.assertEqual(data["days"][0]["civil_date"], entry["first_civil_date"])
                self.assertEqual(data["days"][-1]["civil_date"], entry["last_civil_date"])
                self.assertEqual(
                    [row["common_date"]["ordinal"] for row in data["days"]],
                    list(range(1, 365)),
                )
                year_files[entry["year"]] = data["days"]

            self.assertEqual(
                year_files[2026][0]["calendar_address"], "Y_2026-001",
            )
            self.assertEqual(
                year_files[2026][-1]["calendar_address"], "Y_2026-364",
            )
            self.assertEqual(
                year_files[2027][0]["civil_date"], "2026-12-31",
            )
            self.assertEqual(
                year_files[2027][0]["calendar_address"], "Y_2027-001",
            )
            self.assertEqual(
                year_files[2075][-1]["calendar_address"], "Y_2075-364",
            )

            # The browser's visible values must match the original Core payload,
            # not an independently implemented date/calendar algorithm.
            record = year_files[2027][0]
            source = calendar_day_payload(2027, 1)
            self.assertEqual(record["common_date"], {
                k: source["common_date"][k]
                for k in ("year", "month", "day", "ordinal",
                          "week", "day_in_week", "weekday")
            })
            self.assertEqual(record["sacred_date"], source["sacred_date"])
            self.assertEqual(record["jubilee"]["year"], source["jubilee"]["year"])

    def test_no_unpublished_year_or_nonmonotone_selection(self):
        with tempfile.TemporaryDirectory() as td:
            for years in ([2076], [2027, 2026], [2026, 2026], []):
                with self.subTest(years=years), self.assertRaises(ValueError):
                    export_site(Path(td), years=years)

    def test_site_is_standalone_and_uses_only_exported_data_urls(self):
        site = Path(__file__).resolve().parents[2] / "site" / "stillpoint-calendar" / "index.html"
        text = site.read_text(encoding="utf-8")
        self.assertIn('fetch("./data/index.json"', text)
        self.assertIn('fetch("./" + entry.path', text)
        self.assertIn('id="civilDate"', text)
        self.assertIn('id="weekDays"', text)
        self.assertIn("complete_publication !== true", text)
        self.assertNotIn("OPENAI_API_KEY", text)
        self.assertNotIn("XAI_API_KEY", text)
        self.assertNotIn("github_token", text)


if __name__ == "__main__":
    unittest.main()
