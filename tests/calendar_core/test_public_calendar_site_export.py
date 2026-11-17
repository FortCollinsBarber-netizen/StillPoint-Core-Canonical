"""Tests for the browser export using ONLY the already-public canonical Core.

A partial test build uses 2026, 2027, and 2075 for speed. A production export
must contain all 50 years and explicitly announces that fact in its manifest.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
import tempfile
import unittest

from tools.export_public_calendar_site import export_site
from stillpoint.calendar_core.runtime_surface import calendar_day_payload
from stillpoint.public_assistant import verify_answer_receipt


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
                manifest["assistant_schema"], "stillpoint.public-assistant-static-weeks.v1",
            )
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

                assistant_bytes = (root / entry["assistant_path"]).read_bytes()
                self.assertEqual(
                    hashlib.sha256(assistant_bytes).hexdigest(),
                    entry["assistant_sha256"],
                )
                assistant = json.loads(assistant_bytes)
                self.assertEqual(
                    assistant["schema"], manifest["assistant_schema"],
                )
                self.assertEqual(assistant["year"], entry["year"])
                self.assertEqual(
                    assistant["publication_digest"], manifest["publication_digest"],
                )
                self.assertEqual(entry["assistant_week_count"], 52)
                self.assertEqual(len(assistant["receipts"]), 52)
                for number, receipt in enumerate(assistant["receipts"], start=1):
                    self.assertEqual(
                        receipt["request"],
                        f"Show Common Calendar week {number} of {entry['year']}.",
                    )
                    self.assertEqual(receipt["result"]["week"], number)
                    self.assertEqual(len(receipt["result"]["days"]), 7)
                    self.assertEqual(
                        receipt["authorization"]["capability"], "calendar.week.read",
                    )
                    self.assertFalse(receipt["authorization"]["execution_warrant"])
                    self.assertTrue(verify_answer_receipt(receipt)["verified"])
                # The file digest and the installed Core reproduction are
                # distinct: a tampered result does not become valid by rehashing.
                tampered = dict(assistant["receipts"][0])
                tampered["answer"] = "Common year 2076 is published."
                self.assertFalse(verify_answer_receipt(tampered)["verified"])

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


    @unittest.skipUnless(shutil.which("node"), "Node.js required to execute browser parser contract")
    def test_typed_question_parser_executes_and_fails_closed(self):
        """Execute the actual embedded JavaScript grammar, not a Python rewrite."""
        site = Path(__file__).resolve().parents[2] / "site" / "stillpoint-calendar" / "index.html"
        node_script = r"""
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const html = fs.readFileSync(process.argv[1], "utf8");
const start = html.indexOf("    function parsePublicWeekQuestion(text)");
const end = html.indexOf("    function node(tag, text)", start);
assert.ok(start >= 0 && end > start, "question parser must be present");
const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(html.slice(start, end), sandbox);
function shape(value) { return JSON.parse(JSON.stringify(value)); }
assert.deepEqual(shape(sandbox.parsePublicWeekQuestion("Show Common Calendar week 46 of 2026.")),
  {kind:"week", year:2026, week:46});
assert.deepEqual(shape(sandbox.parsePublicWeekQuestion("display stillpoint week 52 in 2075!")),
  {kind:"week", year:2075, week:52});
assert.deepEqual(shape(sandbox.parsePublicWeekQuestion("Which Common Calendar week contains 2026-11-17?")),
  {kind:"civil_date", civil_date:"2026-11-17"});
for (const invalid of [
  "Show Common Calendar week 0 of 2026.",
  "Show Common Calendar week 53 of 2026.",
  "Show Common Calendar week 1 of 2076.",
  "Show Common Calendar week 1 of 2025.",
  "Send an email to my contacts",
  "Show every week forever",
  "What day is tomorrow?"
]) {
  assert.throws(() => sandbox.parsePublicWeekQuestion(invalid), invalid);
}
console.log("Executed bounded public week question grammar: PASS");
"""
        proc = subprocess.run(
            [shutil.which("node"), "-e", node_script, str(site)],
            capture_output=True, text=True, check=False, timeout=15,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("PASS", proc.stdout)

    def test_site_is_standalone_and_uses_only_exported_data_urls(self):
        site = Path(__file__).resolve().parents[2] / "site" / "stillpoint-calendar" / "index.html"
        text = site.read_text(encoding="utf-8")
        self.assertIn('fetch("./data/index.json"', text)
        self.assertIn('fetch("./" + entry.path', text)
        self.assertIn('id="civilDate"', text)
        self.assertIn('id="weekDays"', text)
        self.assertIn('id="askWeek"', text)
        self.assertIn('id="questionForm"', text)
        self.assertIn('id="weekQuestion"', text)
        self.assertIn('id="questionStatus"', text)
        self.assertIn('parsePublicWeekQuestion(text)', text)
        self.assertIn('week < 1 || week > 52', text)
        self.assertIn('year < 2026 || year > 2075', text)
        self.assertIn('selectionToken !== originalSelection', text)
        self.assertIn('await showAssistantWeek()', text)
        self.assertIn('No unrestricted AI or actions.', text)
        self.assertIn('id="downloadAnswer"', text)
        self.assertIn('id="assistantReceiptHash"', text)
        self.assertIn('window.crypto.subtle.digest("SHA-256", bytes)', text)
        self.assertIn('fetch("./" + entry.assistant_path', text)
        self.assertIn("This static page does not run Python", text)
        self.assertIn("complete_publication !== true", text)
        self.assertNotIn("OPENAI_API_KEY", text)
        self.assertNotIn("XAI_API_KEY", text)
        self.assertNotIn("github_token", text)


if __name__ == "__main__":
    unittest.main()
