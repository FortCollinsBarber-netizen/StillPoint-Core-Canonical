"""Tests for the browser export using ONLY the already-public canonical Core.

A partial test build uses 2026, 2027, and 2075 for speed. A production export
must contain all 50 years and explicitly announces that fact in its manifest.
"""
from __future__ import annotations

import gzip
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

    def test_finite_observance_index_has_only_core_projected_occurrences(self):
        with tempfile.TemporaryDirectory(prefix="stillpoint-observance-index-") as td:
            root = Path(td)
            manifest = export_site(root, years=[2026, 2027, 2075])
            path = root / manifest["observance_index_path"]
            original = path.read_bytes()
            self.assertEqual(hashlib.sha256(original).hexdigest(),
                             manifest["observance_index_sha256"])
            index = json.loads(original)
            self.assertEqual(index["schema"], "stillpoint.public-observance-index.v1")
            self.assertEqual(index["publication_digest"], manifest["publication_digest"])
            self.assertEqual(index["year_count"], 3)
            self.assertEqual(index["first_common_year"], 2026)
            self.assertEqual(index["last_common_year"], 2075)
            self.assertEqual(index["occurrence_count"], manifest["observance_index_count"])
            self.assertEqual(index["jurisdictions"], manifest["observance_index_jurisdictions"])
            expected = []
            for entry in manifest["years"]:
                shard = json.loads((root / entry["path"]).read_bytes())
                for day in shard["days"]:
                    for observance in day["observances"]:
                        expected.append({
                            "calendar_address": day["calendar_address"],
                            "civil_date": day["civil_date"],
                            "common_date": day["common_date"],
                            **observance,
                        })
            self.assertEqual(index["rows"], expected)
            self.assertLess(len(index["rows"]), 10_000)
            self.assertFalse(any(row["common_date"]["year"] == 2076
                                 for row in index["rows"]))
            # Ordinary Gregorian translation at the new Common year's start
            # must be inherited from Core, not recalculated by search.
            self.assertTrue(any(row["calendar_address"] == "Y_2027-001"
                                and row["civil_date"] == "2026-12-31"
                                and row["name"] == "New Year's Day"
                                for row in index["rows"]))
            self.assertTrue(any(row["name"] == "Passover"
                                and "Leviticus 23:5" in row["source_refs"]
                                and row["projection_status"] != "civil-enacted-law"
                                for row in index["rows"]))

    @unittest.skipUnless(shutil.which("node"), "Node.js required to execute real search filter")
    def test_observance_index_browser_integrity_and_filters_execute(self):
        with tempfile.TemporaryDirectory(prefix="stillpoint-observance-search-") as td:
            root = Path(td)
            export_site(root, years=[2026, 2027, 2075])
            site = root / "index.html"
            manifest = root / "data/index.json"
            index = root / "data/observances.json"
            script = r"""
const fs = require("node:fs");
const vm = require("node:vm");
const crypto = require("node:crypto");
const assert = require("node:assert/strict");
const html = fs.readFileSync(process.argv[1], "utf8");
const manifest = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const original = fs.readFileSync(process.argv[3]);
const start = html.indexOf("    async function getObservanceIndex()");
const end = html.indexOf("    function parsePublicWeekQuestion(text)", start);
assert.ok(start >= 0 && end > start, "real search must be present");
let served = original;
const sandbox = {
  manifest, observanceIndexPromise:null, TextDecoder,
  sha256Hex: async bytes =>
    crypto.createHash("sha256").update(Buffer.from(bytes)).digest("hex"),
  chooseYear: civil => manifest.years.find(x =>
    x.first_civil_date <= civil && civil <= x.last_civil_date),
  fetch: async url => {
    assert.match(url, /data\/observances\.json[?]sha256=[a-f0-9]{64}$/);
    return {ok:true, arrayBuffer:async () =>
      served.buffer.slice(served.byteOffset, served.byteOffset+served.byteLength)};
  }
};
vm.createContext(sandbox);
vm.runInContext(html.slice(start,end), sandbox);
const filters = (changes={}) => ({name:"", jurisdiction:"", year:null,
  civil_date:"", ...changes});
(async () => {
  const index = await sandbox.getObservanceIndex();
  assert.equal(index.rows.length, index.occurrence_count);
  const passovers = sandbox.filterObservanceOccurrences(index, filters({name:"passover"}));
  assert.equal(passovers.total, 3);
  assert.equal(passovers.rows.length, 3);
  assert.ok(passovers.rows.every(x => x.name === "Passover"));
  const civic = sandbox.filterObservanceOccurrences(index,
    filters({name:"New Year\'s Day",jurisdiction:"civic",year:2027}));
  assert.equal(civic.total, 1);
  assert.equal(civic.rows[0].calendar_address, "Y_2027-001");
  assert.equal(civic.rows[0].civil_date, "2026-12-31");
  const date = sandbox.filterObservanceOccurrences(index,
    filters({civil_date:"2026-12-31"}));
  assert.ok(date.rows.some(x => x.name === "New Year's Day"));
  const absent = sandbox.filterObservanceOccurrences(index,
    filters({name:"An Event That Is Not In Core"}));
  assert.equal(absent.total, 0);
  for (const bad of [
    filters(), filters({name:"p"}), filters({year:2076}),
    filters({civil_date:"2076-01-01"}), filters({jurisdiction:"unknown"})
  ]) assert.throws(() => sandbox.filterObservanceOccurrences(index,bad));
  sandbox.observanceIndexPromise = null;
  served = Buffer.concat([original, Buffer.from(" ")]);
  await assert.rejects(sandbox.getObservanceIndex(),
    /SHA-256 integrity check/);
  console.log("Real bounded observance browser search and SHA-256: PASS");
})().catch(err => { console.error(err); process.exitCode = 1; });
"""
            completed = subprocess.run(
                [shutil.which("node"), "-e", script, str(site),
                 str(manifest), str(index)],
                capture_output=True, text=True, check=False, timeout=25,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("PASS", completed.stdout)

    def test_gzipped_day_and_observance_receipts_reproduce_from_public_core(self):
        with tempfile.TemporaryDirectory(prefix="stillpoint-detail-receipts-") as td:
            root = Path(td)
            manifest = export_site(root, years=[2026, 2027, 2075])
            self.assertEqual(manifest["day_receipt_schema"],
                             "stillpoint.public-assistant-static-day-receipts.v1")
            self.assertEqual(manifest["observance_receipt_schema"],
                             "stillpoint.public-assistant-static-observance-receipts.v1")
            self.assertEqual(manifest["receipt_format"], "gzip-json-mtime-zero")
            self.assertEqual(manifest["day_receipt_total"], 3 * 364)
            self.assertEqual(manifest["observance_receipt_total"], 3 * 364)
            self.assertTrue(manifest["no_2076_publication"])
            for entry in manifest["years"]:
                with self.subTest(year=entry["year"]):
                    for kind, prefix, capability in (
                        ("day", "day_receipt", "calendar.day.read"),
                        ("observances", "observance_receipt",
                         "calendar.observances.read"),
                    ):
                        location = root / entry[prefix + "_path"]
                        blob = location.read_bytes()
                        self.assertTrue(location.name.endswith(".json.gz"))
                        self.assertLess(len(blob), 5_000_000)
                        self.assertEqual(hashlib.sha256(blob).hexdigest(),
                                         entry[prefix + "_sha256"])
                        self.assertEqual(entry[prefix + "_count"], 364)
                        uncompressed = gzip.decompress(blob)
                        self.assertLess(len(uncompressed), 12_000_000)
                        obj = json.loads(uncompressed)
                        self.assertEqual(obj["year"], entry["year"])
                        self.assertEqual(obj["capability"], capability)
                        self.assertEqual(obj["publication_digest"],
                                         manifest["publication_digest"])
                        self.assertEqual(len(obj["receipts"]), 364)
                        for ordinal in (1, 97, 321, 364):
                            receipt = obj["receipts"][ordinal - 1]
                            self.assertEqual(receipt["status"], "completed")
                            self.assertEqual(receipt["interpretation"]["capability"],
                                             capability)
                            self.assertEqual(receipt["result"]["common_date"]["ordinal"],
                                             ordinal)
                            self.assertFalse(receipt["authorization"]["execution_warrant"])
                            self.assertTrue(verify_answer_receipt(receipt)["verified"])
                        if kind == "observances" and entry["year"] == 2026:
                            self.assertEqual(
                                obj["receipts"][320]["result"]["observances"], []
                            )
            self.assertFalse((root / "data/assistant/day/Y_2076.json.gz").exists())
            self.assertFalse((root / "data/assistant/observances/Y_2076.json.gz").exists())

    @unittest.skipUnless(shutil.which("node"), "Node.js required to run the receipt loader")
    def test_actual_browser_receipt_loader_rejects_tampered_gzip(self):
        with tempfile.TemporaryDirectory(prefix="stillpoint-detail-loader-") as td:
            root = Path(td)
            manifest = export_site(root, years=[2027])
            entry = manifest["years"][0]
            site = root / "index.html"
            index = root / "data" / "index.json"
            day_blob = root / entry["day_receipt_path"]
            obs_blob = root / entry["observance_receipt_path"]
            script = r"""
const fs = require("node:fs");
const vm = require("node:vm");
const crypto = require("node:crypto");
const assert = require("node:assert/strict");
const {DecompressionStream} = require("node:stream/web");
const html = fs.readFileSync(process.argv[1], "utf8");
const manifest = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const day = fs.readFileSync(process.argv[3]);
const obs = fs.readFileSync(process.argv[4]);
const start = html.indexOf("    async function getDetailReceiptShard(entry, kind)");
const end = html.indexOf("    async function getAssistantShard(entry)",start);
assert.ok(start>=0 && end>start, "real gzip receipt loader must exist");
let served = day;
const sandbox = {
  manifest, detailReceiptCache:new Map(), Blob, Response, DecompressionStream,
  TextDecoder, Uint8Array,
  sha256Hex:async bytes=>crypto.createHash("sha256")
    .update(Buffer.from(bytes)).digest("hex"),
  fetch:async url=>{
    assert.match(url, /data\/assistant\/(day|observances)\/Y_2027\.json\.gz[?]sha256=/);
    return {ok:true, arrayBuffer:async()=>
      served.buffer.slice(served.byteOffset,served.byteOffset+served.byteLength)};
  }
};
vm.createContext(sandbox);
vm.runInContext(html.slice(start,end),sandbox);
(async()=>{
  const entry=manifest.years[0];
  const d=await sandbox.getDetailReceiptShard(entry,"day");
  assert.equal(d.receipts.length,364);
  assert.equal(d.receipts[0].request,"Show Common Calendar day 1 of 2027.");
  sandbox.detailReceiptCache.clear();
  served=obs;
  const o=await sandbox.getDetailReceiptShard(entry,"observances");
  assert.equal(o.receipts.length,364);
  assert.equal(o.receipts[0].request,
    "Explain Common Calendar observances on Common day 1 of 2027.");
  sandbox.detailReceiptCache.clear();
  served=Buffer.concat([obs,Buffer.from(" ")]);
  await assert.rejects(sandbox.getDetailReceiptShard(entry,"observances"),
    /manifest SHA-256 check/);
  sandbox.detailReceiptCache.clear();
  served=day;
  await assert.rejects(sandbox.getDetailReceiptShard(
    {...entry,day_receipt_sha256:"0".repeat(64)},"day"),
    /manifest SHA-256 check/);
  await assert.rejects(sandbox.getDetailReceiptShard(entry,"execute"),
    /Unsupported read-only receipt type/);
  console.log("Real gzip receipt browser integrity and scope: PASS");
})().catch(error=>{console.error(error);process.exitCode=1});
"""
            completed = subprocess.run(
                [shutil.which("node"), "-e", script,
                 str(site), str(index), str(day_blob), str(obs_blob)],
                capture_output=True, text=True, check=False, timeout=30,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("PASS", completed.stdout)

    @unittest.skipUnless(shutil.which("node"), "Node.js required for real receipt inspection")
    def test_browser_receipt_inspector_executes_self_hash_and_archive_comparison(self):
        """Execute the browser inspector against real Python-issued saved receipts."""
        with tempfile.TemporaryDirectory(prefix="stillpoint-receipt-inspector-") as td:
            root = Path(td)
            manifest = export_site(root, years=[2026, 2027, 2075])
            site = root / "index.html"
            mpath = root / "data/index.json"
            day = root / manifest["years"][0]["day_receipt_path"]
            observance = root / manifest["years"][1]["observance_receipt_path"]
            week = root / manifest["years"][0]["assistant_path"]
            historical = (Path(__file__).resolve().parents[2] / "docs/examples/archive"
                          / "public_assistant_week_answer_0261e0c_pre_observance.json")
            self.assertTrue(historical.is_file())
            code = r"""
const fs = require("node:fs");
const vm = require("node:vm");
const crypto = require("node:crypto");
const zlib = require("node:zlib");
const assert = require("node:assert/strict");
const html = fs.readFileSync(process.argv[1],"utf8");
const manifest = JSON.parse(fs.readFileSync(process.argv[2],"utf8"));
const day = JSON.parse(zlib.gunzipSync(fs.readFileSync(process.argv[3]))
  .toString("utf8"));
const observance = JSON.parse(zlib.gunzipSync(fs.readFileSync(process.argv[4]))
  .toString("utf8"));
const week = JSON.parse(fs.readFileSync(process.argv[5],"utf8"));
const archived = JSON.parse(fs.readFileSync(process.argv[6],"utf8"));
const start = html.indexOf("    function canonicalReceiptJson(value, depth)");
const end = html.indexOf("    function parsePublicWeekQuestion(text)",start);
assert.ok(start>=0 && end>start,"real in-page receipt inspector must exist");
let detailFetchCount=0, weekFetchCount=0;
const sandbox = {
 manifest, TextEncoder,
 sha256Hex:async bytes=>crypto.createHash("sha256")
   .update(Buffer.from(bytes)).digest("hex"),
 getDetailReceiptShard:async(entry,kind)=>{
   detailFetchCount+=1;
   assert.ok([2026,2027].includes(entry.year));
   return kind==="day" ? day : observance;
 },
 getAssistantShard:async(entry)=>{
   weekFetchCount+=1;
   assert.equal(entry.year,2026);
   return week;
 }
};
vm.createContext(sandbox);
vm.runInContext(html.slice(start,end),sandbox);
const clone = value=>JSON.parse(JSON.stringify(value));
async function digestWithoutSelf(receipt) {
  const {receipt_sha256, ...unsigned}=receipt;
  return crypto.createHash("sha256")
    .update(sandbox.canonicalReceiptJson(unsigned)).digest("hex");
}
(async()=>{
  const originals = [
    day.receipts[320], observance.receipts[96], week.receipts[45],
  ];
  for(const receipt of originals) {
    assert.equal(await digestWithoutSelf(receipt),receipt.receipt_sha256);
    const report=await sandbox.inspectReceiptAgainstPublication(clone(receipt));
    assert.equal(report.matched,true);
    assert.equal(report.disposition,"current-match");
    assert.equal(report.self_hash_valid,true);
    assert.equal(report.receipt_sha256,receipt.receipt_sha256);
    assert.equal(report.publication_digest,manifest.publication_digest);
    assert.ok(report.sources.length>=10);
  }
  const tampered=clone(day.receipts[320]);
  tampered.answer="An unsupported holiday has been created.";
  await assert.rejects(sandbox.inspectReceiptAgainstPublication(tampered),
    /self-hash mismatch/i);
  const forged=clone(day.receipts[320]);
  forged.answer="An unsupported holiday has been created.";
  forged.receipt_sha256=await digestWithoutSelf(forged);
  const forgedReport=await sandbox.inspectReceiptAgainstPublication(forged);
  assert.equal(forgedReport.matched,false);
  assert.equal(forgedReport.disposition,"current-difference");
  assert.equal(forgedReport.claimed_publication_digest,manifest.publication_digest);
  const warrant=clone(day.receipts[320]);
  warrant.authorization.execution_warrant=true;
  warrant.receipt_sha256=await digestWithoutSelf(warrant);
  await assert.rejects(sandbox.inspectReceiptAgainstPublication(warrant),
    /read-only/);
  const future=clone(day.receipts[320]);
  future.result.common_date.year=2076;
  future.interpretation.arguments.year=2076;
  future.request="Show Common Calendar day 321 of 2076.";
  future.receipt_sha256=await digestWithoutSelf(future);
  await assert.rejects(sandbox.inspectReceiptAgainstPublication(future),
    /unpublished Common year/);
  const unsupported=clone(day.receipts[320]);
  unsupported.interpretation.capability="calendar.day.write";
  unsupported.receipt_sha256=await digestWithoutSelf(unsupported);
  await assert.rejects(sandbox.inspectReceiptAgainstPublication(unsupported),
    /unsupported or consequential/);
  const badScope=clone(observance.receipts[96]);
  badScope.evidence.publication_digest="0".repeat(64);
  badScope.receipt_sha256=await digestWithoutSelf(badScope);
  const beforeHistorical=detailFetchCount;
  const historicalClaim=await sandbox.inspectReceiptAgainstPublication(badScope);
  assert.equal(historicalClaim.disposition,"different-publication-claimed");
  assert.equal(historicalClaim.matched,false);
  assert.equal(historicalClaim.claimed_publication_digest,"0".repeat(64));
  assert.equal(historicalClaim.sources.length,0);
  assert.equal(detailFetchCount,beforeHistorical,
    "a claimed older publication must not fetch an untrusted historical archive");
  const malformedDigest=clone(observance.receipts[96]);
  malformedDigest.evidence.publication_digest="not-a-sha";
  malformedDigest.receipt_sha256=await digestWithoutSelf(malformedDigest);
  await assert.rejects(
    sandbox.inspectReceiptAgainstPublication(malformedDigest),/invalid claimed publication digest/);

  const stale=clone(week.receipts[45]);
  stale.evidence.sources[0].sha256="0".repeat(64);
  stale.receipt_sha256=await digestWithoutSelf(stale);
  const staleReport=await sandbox.inspectReceiptAgainstPublication(stale);
  assert.equal(staleReport.matched,false);
  assert.equal(staleReport.disposition,"current-difference");
  // This is an actual unchanged public historical receipt preserved in Core,
  // not a fabricated older-version example. The old civil-date request shape
  // must be explained, but never accepted as a verified current archive match.
  assert.equal(await digestWithoutSelf(archived),archived.receipt_sha256);
  const beforeOldWeek=weekFetchCount;
  const oldReport=await sandbox.inspectReceiptAgainstPublication(clone(archived));
  assert.equal(oldReport.disposition,"older-read-request-unverified");
  assert.equal(oldReport.matched,false);
  assert.equal(oldReport.sources.length,0);
  assert.equal(weekFetchCount,beforeOldWeek);
  const unsafeOld=clone(archived);
  unsafeOld.request="Delete all Calendar records.";
  unsafeOld.receipt_sha256=await digestWithoutSelf(unsafeOld);
  await assert.rejects(sandbox.inspectReceiptAgainstPublication(unsafeOld),
    /supported read-only Common Calendar coordinate/);
  console.log("Browser exact receipt self-hash and public archive comparison: PASS");
})().catch(error=>{console.error(error);process.exitCode=1});
"""
            run = subprocess.run(
                [shutil.which("node"), "-e", code,
                 str(site), str(mpath), str(day), str(observance), str(week),
                 str(historical)],
                capture_output=True, text=True, check=False, timeout=40,
            )
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertIn("PASS",run.stdout)

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
  fetch: async (url) => {
    assert.match(url, /[?]sha256=[a-f0-9]{64}$/);
    return {ok:true, arrayBuffer:async () =>
      served.buffer.slice(served.byteOffset, served.byteOffset+served.byteLength)};
  }
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
        self.assertIn('id="observanceSearchForm"', text)
        self.assertIn('id="observanceSearchResults"', text)
        self.assertIn('async function getObservanceIndex()', text)
        self.assertIn('filterObservanceOccurrences(index, filters)', text)
        self.assertIn('entry.observance_index_sha256', text)
        self.assertIn('row.common_date.year !== filters.year', text)
        self.assertIn('No named Core occurrences matched', text)
        self.assertIn('invalidateDetailReceiptSelection(', text)
        self.assertIn('activeReceiptDay = null;', text)
        self.assertIn('id="receiptInspectorForm"', text)
        self.assertIn('id="receiptInspectorNextSteps"', text)
        self.assertIn('aria-atomic="true" tabindex="-1"', text)
        self.assertIn('aria-controls="receiptInspectorResult"', text)
        self.assertIn('aria-describedby="receiptInspectorHint"', text)
        self.assertIn('DIFFERENT PUBLICATION CLAIM:', text)
        self.assertIn('OLDER READ REQUEST SHAPE (UNVERIFIED):', text)
        self.assertIn('CURRENT DIFFERENCE:', text)
        self.assertIn('receiptInspectorStatus").focus()', text)
        self.assertIn('setAttribute("aria-busy","true")', text)
        self.assertIn('id="receiptInspectorStatus"', text)
        self.assertIn('id="receiptInspectorSources"', text)
        self.assertIn('async function inspectReceiptAgainstPublication(receipt)', text)
        self.assertIn('canonicalReceiptJson(unsigned)', text)
        self.assertIn('const matched = canonicalReceiptJson(receipt)', text)
        self.assertIn('window.crypto', text)
        self.assertIn('id="saveDayReceipt"', text)
        self.assertIn('id="saveObservanceReceipt"', text)
        self.assertIn('async function getDetailReceiptShard(entry, kind)', text)
        self.assertIn('new DecompressionStream("gzip")', text)
        self.assertIn('data.day_receipt_total !== 18200', text)
        self.assertIn('data.observance_receipt_total !== 18200', text)
        self.assertIn('await sha256Hex(bytes) !== sha', text)
        self.assertIn('receipt.authorization.execution_warrant !== false', text)
        self.assertIn('id="dayQuestionForm"', text)
        self.assertIn('id="dayQuestionStatus"', text)
        self.assertIn('id="dayObservanceEvidence"', text)
        self.assertIn('parsePublicDayQuestion(text)', text)
        self.assertIn('await sha256Hex(bytes) !== entry.sha256', text)
        self.assertIn('entry.path + "?sha256=" + entry.sha256', text)
        self.assertIn('entry.assistant_path + "?sha256=" + entry.assistant_sha256', text)
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
