# Public observance search — Core-grounded, finite, read-only v1

## Purpose and release classification

This is an additive **public Canonical Core static browser** capability: people
can locate **named occurrences already declared by the existing published
Core** without making StillPoint create, move, interpret, or impose any
observance. A feature PR or a successful branch test is **not** a production
Pages release; independently verify the merged source and live browser.

The selected Common Calendar publication remains **2026–2075 only**:
50 × 364 = **18,200 day records**. Common year **2076** is mathematical only
and has no published day or observance index entry. Nothing here changes the
March 25 selected sacred source-year anchor, independently selected 2027
Jubilee epoch or overlapping 49-year rule, or the separate 364-day Common
civil surface.

## What a person can do on the public website

Use the **Search published observances** form to combine any of these
filters: a case-insensitive name substring (minimum two characters), an exact
Core *jurisdiction* from the index, a **Common** year 2026–2075, and/or an
exact **ordinary Gregorian translation date** within the public projection.

The user must specify at least one filter, to prevent an unbounded query.
Results appear in Core's existing chronological occurrence order, with a
**total match count** and at most **30 visible occurrences**. Each result
preserves the Core's published name, Common address, ordinary date
translation, jurisdiction, rule, projection status, recorded source
references and optional original note. **Explore this published day** opens
the existing SHA-checked Common date browser; no new calendar arithmetic.

Examples:

- Name `Passover`: find the author-selected sacred-source recurrence across
  published years and see the recorded scriptural references, source
  coordinate, jurisdiction, and interpretive status.
- Jurisdiction `civic`, Common year `2027`: retrieve only those Common
  civic occurrences in that published year.
- Ordinary date `2026-12-31`: locate the published **Common 2027 day 1**
  observance(s). This is a translation label; the Gregorian calendar does
  **not** control Common-year boundaries.
- Name `event not in core`: report zero matches rather than guessing or
  generating an invented holiday.

A title, source reference, or Common-grid observance does not make an event
universally binding, substitute for a community's selected religious or
civil calendar, establish jurisdiction over people, or calculate local dusk
and dawn. Historic 2026 external examples not present in Core's published
observance projection cannot be silently promoted to recurring observances.

## Source and integrity chain

The existing exporter calls
`stillpoint.calendar_core.runtime_surface.calendar_day_payload()` for
all published days, then projects each day's original observance annotation.
It emits an additive file, `data/observances.json`, whose occurrences are
derived **only** from those already-exported day rows, not independently
computed from calendars, equations, or references.

The manifest `data/index.json` records:

- `observance_index_schema`: `stillpoint.public-observance-index.v1`;
- `observance_index_path`: `data/observances.json`;
- `observance_index_sha256`: SHA-256 digest of the exact JSON bytes;
- `observance_index_count`: finite number of indexed occurrences;
- `observance_index_jurisdictions`: the actual available Core jurisdictions.

The browser requests the index with its manifest SHA-256 as a cache-versioned
URL query; then computes SHA-256 over the retrieved bytes, validates
publication digest and 2026–2075 scope, and rejects invalid/mismatched
records. The browser does **not** assign dates, recalculate recurrence
rules, execute new Python, or connect to any private services.

The index's fingerprint confirms **agreement with the unsigned public site
manifest**, not a trusted signature, proof of original author consent, or
an independently reproducible Python assistant receipt. For an authoritative
day-specific full receipt, use the existing bounded CLI
`stillpoint ask` and `stillpoint verify-answer` against matching Core
source and public data. The index is a search convenience, not a new
`calendar.observances.read` permission grant.

## Executable regression qualification

```sh
python -m unittest discover -s tests/calendar_core -p 'test_public_calendar_site_export.py' -v
python tools/export_public_calendar_site.py --output /tmp/stillpoint-public-browser
```

The index regression proves an exact deep equality between every indexed
occurrence and the corresponding precomputed Core day shard, including
the 2026/2027 translation rollover, source references, notes and the
exclusion of 2076. An additional Node VM test executes **the actual browser
filter function and SHA-256 index loader**; it accepts known civic/sacred
examples, proves case-insensitive matching and Combined filters, rejects
unbounded/invalid requests, and fails on a byte-tampered index.

Release also requires the existing **public** GitHub Actions gates and an
independent live-browser test of the exact deployed Pages source; code diff,
workflow status, full SHA, UTC evidence and useful outcomes belong in public
coordination [issue #88](https://github.com/FortCollinsBarber-netizen/StillPoint-Core-Canonical/issues/88).

No new workflow, repository, paid runner or separate hosting. The private
`RobertOS`, `StillPointOS`, `StillPoint` and `writing-corpus` repositories
remain private, unmodified and unqualified for current live integration.
