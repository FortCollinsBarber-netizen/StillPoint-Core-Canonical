# Browser receipt inspection — public read-only v1

**Release status:** receipt inspection v1 shipped on public Canonical Core at
`e9b514704fc34db212d602fa3c396b0da6211d93`. The follow-on historical
receipt explanation and keyboard accessibility changes remain a **candidate**
until the new exact merged `main` SHA passes post-merge public CI, automatic
Pages publication and independent live browser acceptance.

## Why this matters

People can already save StillPoint's precomputed, Python-verified day,
observance and week receipts from the public calendar without installing
Python. Now the same static website can **inspect an existing JSON receipt
chosen from their own computer** and distinguish **three different evidence
levels** that must never be collapsed into one claim.

1. **Self-hash check:** canonicalizes the JSON fields using the published
   Python assistant's sorted-key, UTF-8, compact JSON hash convention
   (integer-valued public Core schema only). Checks the receipt's own
   `receipt_sha256` after excluding that field. A valid checksum establishes
   *internal consistency only*: an adversary can modify content and recalculate
   this hash. It is not a signature, identity or consent proof.
2. **Current published archive match:** locates the exact selected Common
   day/observance or week within published years **2026–2075**. Loads only
   the site's existing Core-produced receipt shard, verifies its **exact bytes**
   by SHA-256 against the public manifest, checks finite, read-only scope,
   and compares the **complete** saved receipt with the public
   Python-build-verified original (canonical key order, not just a digest
   or selected fields). A rehashed forged receipt fails this match.
   Older-but-valid historical source versions may not match the *current*
   archive; this is not conclusive evidence of malice.
3. **Independent Python reproduction:** remains the strongest available
   correctness test: using the *matching* public Python Core source/data, run
   `stillpoint verify-answer saved-receipt.json`. The browser **does not
   execute Python** or verify that the publisher's source is authenticated.
   Neither an exact archive match nor a Python result constitutes a signature,
   civil/religious enactment, personal authorization, or private integration
   qualification.

The browser displays the specific public capability
(`calendar.day.read`, `calendar.observances.read` or `calendar.week.read`),
Common year/day or week, receipt SHA-256, publication digest and the exact
**source-file names and SHA-256 fingerprints recorded in the original Core
receipt** after a current-archive match. It does not invent provenance.

## Clearly separated visitor outcomes and historical provenance

An accessible result names **one of five clearly bounded outcomes**, with
ordinary-language next steps instead of implying a signature, fraud verdict,
or archival verification.

- **CURRENT MATCH**: both the self-hash and full content equality with the
  current SHA-256-checked public Core archive passed. The original archive's
  11 recorded source fingerprints can be shown; the local browser still did
  not run the Python verifier.
- **CURRENT DIFFERENCE**: self-hash is consistent and the saved receipt
  claims this publication digest, but the complete content differs from the
  current archive. An older source revision, a changed file, or a rehashed
  forgery may explain it. There is **no evidence here to choose among them**,
  and no archive source fingerprints are accepted.
- **DIFFERENT PUBLICATION CLAIM**: self-hash is consistent, the read-only
  address and request are within the published Common scope, but the receipt
  claims a different well-formed publication digest. The inspector **does not
  fetch or trust a historical archive**, does not certify that the digest
  ever belonged to an official release, and does not display accepted
  current-archive source fingerprints. This is a *claim only*, not proof of
  a legitimate older receipt.
- **PINNED HISTORICAL EXAMPLE MATCH**: *exactly one* public archived
  week receipt is matched against a hard-coded complete receipt digest, after
  its own canonical self-hash has passed. The recognized example is the
  Gregorian-date week request for 2026-11-17, corresponding to Common 2026
  week 46, with receipt SHA-256
  `7173c7bcc915f4b3ea8288b85c520a4ce159929008f7c530c4a294c5f411b2a7`.
  Its public Python source was independently reopened at **full commit
  `0261e0cda145f4eddd9b039cb81e7928a6397859`** and
  `verify_answer_receipt` returned `verified: true` while
  `answer_request` recreated the **identical complete receipt**.
  The archived example is publicly preserved at full commit
  `fa0dca150cd29e598ef07668b12697a213aa6403`, path
  `docs/examples/archive/public_assistant_week_answer_0261e0c_pre_observance.json`.
  Only this exact independently reproduced example is recognized by the
  website. This is **not** a signed original, identity/consent proof, a
  current release match, or general verification of other historical
  receipts. The current browser does not rerun the old Python code.
- **OLDER READ REQUEST SHAPE (UNVERIFIED)**: a narrow, bounded, read-only
  civil-date week-request grammar is recognized from a **preserved actual
  public historical example** at
  `docs/examples/archive/public_assistant_week_answer_0261e0c_pre_observance.json`.
  Its correct original self-hash and recognizable grammar explain why it
  cannot be directly compared with the current week-number request form.
  **Neither its recorded history nor the grammar alone authenticates an
  arbitrary uploaded receipt**; this branch does not fetch older archives,
  accept a current match, or show accepted source fingerprints for this
  outcome. Arbitrary, write-like or unrecognized requests still fail closed.

The inspector displays **both the claimed and current publication digests**
when applicable. To qualify a historical receipt, independently obtain the
exact public Core revision and matching original data that issued it, then
run `stillpoint verify-answer saved-receipt.json` with that revision.
The currently live site's comparison cannot substitute for this.

For keyboard and assistive-technology users, the selected-file input has an
explicit visible label and hint; the submit control is associated with its
result region; the result has a stable heading; the live status is atomic and
receives focus after inspection success or rejection without trapping the
keyboard. Busy state is explicitly communicated while comparisons run.
Selecting a different file clears old result text and provenance, prevents
stale asynchronous results, and returns to the initial inspection state.
Information is communicated by *words*, not by color alone.

## Reproduce the historical example using the pinned public source

The following reference commands use a *public source checkout* and the
*public archived receipt*; use a clean temporary directory. They do not
require a private repository, paid account or private runner. Run a Python
version supported by the pinned repository and do not import current
Core source accidentally. The archived receipt was stored after the
source commit; the source checkout alone does not contain its copy.

```sh
git clone https://github.com/FortCollinsBarber-netizen/StillPoint-Core-Canonical.git public-core-proof
cd public-core-proof
git checkout --detach 0261e0cda145f4eddd9b039cb81e7928a6397859

# Save the archived public JSON example separately, e.g. /tmp/old-week.json,
# from the immutable GitHub blob URL pinned above.
PYTHONPATH=. python -c '
import json
from pathlib import Path
from stillpoint.public_assistant import (
    verify_answer_receipt, answer_request, WEEK_READ
)
receipt = json.loads(Path("/tmp/old-week.json").read_text())
verdict = verify_answer_receipt(receipt)
replayed = answer_request(
    receipt["request"],
    allowed_capabilities=frozenset({WEEK_READ})
)
assert verdict["verified"] is True
assert replayed == receipt
print("PUBLIC_HISTORICAL_RECEIPT_REPRODUCED")
'
```

**Exact evidence already executed:** with the public source zip pinned to
`0261e0cda145f4eddd9b039cb81e7928a6397859` and the archived
public fixture, the Python verifier returned `verified: true`, and
`answer_request` recreated the same receipt SHA-256
`7173c7bcc915f4b3ea8288b85c520a4ce159929008f7c530c4a294c5f411b2a7`.
The browser matches that fixed digest *only after* checking the entire
receipt's canonical self-hash; a rehashed forgery following the same old
request grammar must remain `OLDER READ REQUEST SHAPE (UNVERIFIED)`.
Source publication/reproduction is not a cryptographic signature.

## Secure and bounded behavior

The inspector is a form on the existing public static website. The user's
selected `.json` file is **read locally** with the standard browser File
API. The page does not send that file to an API, email, third-party service,
analytics provider or new backend. **Only previously public static Core
archives** may be fetched from this same Pages website for comparison.

- Maximum local file size: **256,000 bytes**, matching the Python Core's
  read-receipt limit. JSON must be parseable; arbitrary other file formats
  and unsupported request types are rejected without executing file content.
- Only completed original public read receipts are supported; any claimed
  `execution_warrant: true`, write/action capability, missing scope, or
  mathematical-only **Common 2076** is rejected. Day 365, week 53 and
  out-of-map years are also rejected before fetching a shard.
- A matching self-hash with a different result/source fingerprint still
  reports **NOT identical to the current published receipt**. The browser
  does not silently bless a rehashed forgery.
- All file-derived strings are rendered using `textContent`, never as HTML.
  Re-selecting another file invalidates the earlier result, and async
  result tokens prevent a stale comparison from overwriting a newer
  inspection. The receipt is not stored or retained on the site.

The canonical JSON hashing is deliberately scoped to the existing
integer-valued StillPoint public receipt schema: booleans, integers, strings,
nulls, arrays and dictionaries are supported; unsupported floating-point
values, unusually deep nested objects and excessive arrays fail closed.
The actual Node and browser tests compare the browser's digest calculation
to **real Python-generated receipts**, including source references and
their Unicode text.

## Executable qualification

```sh
python -m unittest discover -s tests/calendar_core -p 'test_public_calendar_site_export.py' -v
python tools/export_public_calendar_site.py --output /tmp/stillpoint-inspector-site
```

The new Node VM test evaluates the **actual browser inspector functions**
against the original Python-exported gzip day and observance receipts and the
week JSON shard. Cases include: correct saved day/observance/week receipts;
edited answer with stale checksum; **forged answer with correctly recalculated
checksum**; unsupported write authority; a modified source fingerprint with
correctly recalculated checksum; a self-consistent *different-publication claim*
reported as **unverified without fetching any old archive**; the exact
historical public week example using the previous civil-date request form,
which must receive an **unverified** explanation rather than a current
match; arbitrary unsafe request types; a malformed publication digest;
and Common 2076. An independent live-browser test must also
confirm locally selected files, three distinct accessible outcomes, focus and
announcements for errors, no file uploads, and behavior at mobile width.

The exporter, Core calendar law, current receipt schemas, source map, and
existing fixed annual and week files remain unchanged by this inspector.
No new repository, workflow, paid hosting, model provider, payment, private
runner retry, or private source integration is required.

**Protected boundaries:** the March 25 selected sacred-source anchor; 2027
Jubilee epoch and overlapping 49-year cycle; independently selected 364-day
Common grid; finite published **2026–2075** span. Common **2076 remains
mathematical only**. RobertOS, StillPointOS, StillPoint and writing-corpus
remain private and unchanged. Passing public browser/Core CI **never** proves
their live private bridge has qualified.
