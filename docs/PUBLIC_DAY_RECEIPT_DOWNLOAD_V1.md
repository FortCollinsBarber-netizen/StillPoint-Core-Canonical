# Downloadable public day and observance receipts — static browser v1

**Status:** Candidate public Canonical Core feature. A merged commit and an actual live Pages browser check are required before declaring this released.

## Visitor capability

The public StillPoint website already displays any of the **18,200** published Common days and the original Core observance annotations. This increment adds two direct actions to the selected day: **Save verified day receipt** and **Save verified observance receipt**.

The browser downloads a complete JSON receipt that was generated and *independently reproduced by the Python Core verifier during the public static-site export*:

- `Show Common Calendar day 321 of 2026.` → public `calendar.day.read`;
- `Explain Common Calendar observances on Common day 1 of 2027.` → public `calendar.observances.read`.

An observance-read receipt is also available when a day has **no named observances**. It faithfully records the empty Core result. These requests are preauthorized only for the public, deterministic, read-only projections used at build time. There is no general model, network action, login, consent claim, location collection, private data, or new calendar-law engine.

**Visitors do not need to install or run Python to download the already generated receipts.** Anyone independently verifying reproduction against the precise corresponding Python Core source may still use `stillpoint verify-answer <receipt.json>`; the *browser alone does not independently reexecute Python*. A receipt digest, a matching public-site manifest, and a build-time verifier pass are all distinct from cryptographic signatures, author identity proof, recipient consent, and civil/administrative execution warrants.

## Exact public data and deterministic compression

The existing exporter generates both receipt types directly through:

```python
answer_request(request, allowed_capabilities=frozenset({capability}))
verify_answer_receipt(receipt)["verified"]
```

For **every one** of the 364 days in each published Common year 2026–2075 it computes one complete day receipt and one complete observance read receipt. This is **18,200 per capability, 36,400 total receipts**. Each is required to match its exact Core common year, ordinal, publication digest and read-only authorization, and to reproduce with the existing independent Python verifier. A mismatch fails the whole export; it cannot silently publish a substitute JSON object.

The receipts are packaged as **two gzip-compressed, SHA-256 identified per-year shards**:

- `data/assistant/day/Y_<year>.json.gz`
- `data/assistant/observances/Y_<year>.json.gz`

Python `gzip.compress` uses `mtime=0` for deterministic source reproducibility. A year shard contains exactly 364 read-only answer objects. The published `data/index.json` manifest lists each shard's expected SHA-256, relative path, receipt count, and schema and states that each receipt passed the Python verifier during export.

The browser downloads a shard **only for the selected published year and requested read capability**, computes SHA-256 over the compressed *bytes*, rejects a mismatch, uses the built-in browser `DecompressionStream("gzip")`, checks bounded compressed/decompressed size and finite read-only scope, and then saves the selected complete receipt as a JSON file. It **does not mint receipts or recompute the calendar**.

The manifest itself is unsigned. SHA-256 shows agreement within the published static release; independent source reproduction remains a separate stronger correctness check.

## Time, size and failure boundaries

The finite 2026–2075/364-day mapping remains unchanged. **2076 is mathematical-only and has no downloadable receipt shard.** The March 25 selected sacred-source reference, 2027 Jubilee epoch, overlapping 49-year Jubilee/proclamation, and the separate 364-day Common civil surface remain as published. External Gregorian labels remain translations, not governing Common coordinates.

The browser fails closed when: a shard is absent, its SHA-256 does not match the public manifest, its gzip cannot be decoded, it exceeds the bounded compressed or decompressed size, it has the wrong year, schema, count, capability, receipt status, read-only authorization, original request or publication digest, or the user changes the selected day while the receipt is loading. An older answer is not presented as authority for a new selection. Supported browsers must implement standard HTTPS `crypto.subtle` and `DecompressionStream`.

The gzip shards reduce download size and hosting footprint compared with 36,400 separate uncompressed JSON files. Before deployment, the full 50-year build must report size and duration; any published Pages size or CI limit is an engineering blocker, not a reason to use paid services or waive verification.

## Qualification

Run the existing public browser export suite (including executable Node.js receipt-loader/tamper tests) and the full existing public Core CI on the exact candidate head. Build all 50 years, confirm **36,400 individually reproduced receipts**, 18,200 day projections, 2,600 existing week receipts, the existing 2,450 observance search index entries, no 2076, and SHA-256 of every artifact.

After independently authorized merge, require successful **post-merge** workflow runs for that exact public `main` SHA and a **real live browser** test of day/observance JSON downloads at a normal day, a sacred annotated day, a Common/Gregorian year-boundary day, and 2075 final published day, plus 2076 rejection and mobile viewport. Keep the broader site read-only and preserve the previously qualified week-answer receipt downloads.

This is **public Canonical Core only**. `RobertOS`, `StillPointOS`, `StillPoint`, and `writing-corpus` remain private and unchanged. No private GitHub Actions, billing changes, source mirroring, unqualified private bridge claims, or native device claims.
