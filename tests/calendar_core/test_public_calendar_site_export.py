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

    def test_published_observance_evidence_matches_public_core_exactly(self):
        from stillpoint.calendar_core.observances import SACRED_OBSERVANCES
        passover = next(item for item in SACRED_OBSERVANCES if item.id == "passover")
        for year, ordinal in ((2027, 1), (2027, passover.start_ordinal)):
            with self.subTest(year=year, ordinal=ordinal):
                with tempfile.TemporaryDirectory() as td:
                    manifest = export_site(Path(td), years=[year])
                    entry = manifest["years"][0]
                    shard = json.loads((Path(td) / entry["path"]).read_text())
                    row = shard["days"][ordinal - 1]
                    core = calendar_day_payload(year, ordinal)
                    expected = [
                        {
                            "id": item["id"], "name": item["name"],
                            "jurisdiction": item["jurisdiction"],
                            "rule": item["rule"],
                            "note": item["note"],
                            "source_refs": item["source_refs"],
                            "source_coordinate": item["source_coordinate"],
                            "profile_id": item["profile_id"],
                            "projection_status": item["projection_status"],
                        }
                        for item in core["observances"]
                    ]
                    self.assertEqual(row["observances"], expected)
                    self.assertTrue(row["observances"])
                    self.assertEqual(
                        hashlib.sha256((Path(td) / entry["path"]).read_bytes()).hexdigest(),
                        entry["sha256"],
                    )
                    if ordinal == passover.start_ordinal:
                        self.assertTrue(any(
                            "Leviticus 23:5" in item["source_refs"]
                            for item in row["observances"]
                        ))

    @unittest.skipUnless(shutil.which("node"), "Node.js required for public day query grammar")
    def test_typed_day_and_observance_questions_execute_finite_grammar(self):
        site = Path(__file__).resolve().parents[2] / "site" / "stillpoint-calendar" / "index.html"
        script = r"""
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const html = fs.readFileSync(process.argv[1], "utf8");
const start = html.indexOf("    function parsePublicDayQuestion(text)");
const end = html.indexOf("    function renderCoreDayEvidence(", start);
assert.ok(start >= 0 && end > start, "day parser must be present");
const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(html.slice(start, end), sandbox);
const parse = (input) => JSON.parse(JSON.stringify(sandbox.parsePublicDayQuestion(input)));
assert.deepEqual(parse("What is the Common Calendar date for 2026-11-17?"),
  {kind:"day", civil_date:"2026-11-17"});
assert.deepEqual(parse("Explain the Common Calendar observances for 2026-11-17."),
  {kind:"observances", civil_date:"2026-11-17"});
assert.deepEqual(parse("Show Common Calendar day 364 of 2075."),
  {kind:"day", ordinal:364, year:2075});
assert.deepEqual(parse("List Common Calendar observances on Common day 1 of 2027."),
  {kind:"observances", ordinal:1, year:2027});
for (const denied of [
  "Explain Common Calendar observances on Common day 1 of 2076.",
  "Show Common Calendar day 365 of 2027.",
  "Show Common Calendar day 0 of 2027.",
  "Send a message to my contacts",
  "Explain why every person must follow the observance",
  "What is today?"
]) {
  assert.throws(() => parse(denied), denied);
}
console.log("Executed bounded day and observance query grammar: PASS");
"""
        proc = subprocess.run(
            [shutil.which("node"), "-e", script, str(site)],
            capture_output=True, text=True, check=False, timeout=15,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("PASS", proc.stdout)

    @unittest.skipUnless(shutil.which("node"), "Node.js required to execute actual SHA browser loader")
    def test_browser_year_integrity_rejects_byte_tampering(self):
        """Execute the real JS shard loader against a Core-generated year and a forged copy."""
        with tempfile.TemporaryDirectory(prefix="stillpoint-shard-integrity-") as td:
            root = Path(td)
            export_site(root, years=[2027])
            site = root / "index.html"
            manifest = root / "data" / "index.json"
            year_file = root / "data" / "Y_2027.json"
            node_script = r"""
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const html = fs.readFileSync(process.argv[1], "utf8");
const index = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const entry = index.years[0];
const pristine = fs.readFileSync(process.argv[3]);
const start = html.indexOf("    async function sha256Hex(bytes)");
const end = html.indexOf("    async function getAssistantShard(entry)", start);
assert.ok(start >= 0 && end > start, "real year-shard loader must exist");
let served = pristine;
const sandbox = {
  cache:new Map(), manifest:index, window:{crypto:crypto.webcrypto},
  Uint8Array, TextDecoder,
  fetch: async () => ({ok:true, arrayBuffer:async () =>
    served.buffer.slice(served.byteOffset, served.byteOffset+served.byteLength)})
};
vm.createContext(sandbox);
vm.runInContext(html.slice(start,end), sandbox);
(async () => {
  const result = await sandbox.getShard(entry);
  assert.equal(result.year, 2027);
  assert.equal(result.days.length, 364);
  sandbox.cache.clear();
  served = Buffer.concat([pristine, Buffer.from(" ")]);
  await assert.rejects(sandbox.getShard(entry), /SHA-256 integrity check/);
  sandbox.cache.clear();
  served = pristine;
  await assert.rejects(
    sandbox.getShard({...entry,sha256:"0".repeat(64)}),
    /SHA-256 integrity check/
  );
  console.log("Browser year-shard SHA-256 actual loader: PASS");
})().catch(error => {console.error(error);process.exitCode=1});
"""
            run = subprocess.run(
                [shutil.which("node"), "-e", node_script,
                 str(site), str(manifest), str(year_file)],
                capture_output=True, text=True, check=False, timeout=20,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("PASS", run.stdout)

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
        self.assertIn('An invalid new question must not leave an older answer', text)
        self.assertIn('$("assistantResult").classList.add("hidden");', text)
        self.assertIn('No unrestricted AI or actions.', text)
        self.assertIn('id="dayQuestionForm"', text)
        self.assertIn('id="dayQuestionStatus"', text)
        self.assertIn('id="dayObservanceEvidence"', text)
        self.assertIn('parsePublicDayQuestion(text)', text)
        self.assertIn('await sha256Hex(bytes) !== entry.sha256', text)
        self.assertIn('item.source_refs.join("; ")', text)
        self.assertIn("No named Core observance", text)
        self.assertIn("not a signature or a separate Python answer receipt", text)
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
