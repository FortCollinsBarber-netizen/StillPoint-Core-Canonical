# Patch 040 — Canonical Provenance Closure

Patch 040 closes a release-identity defect exposed immediately after Patch 039 merged.
The runtime code on canonical `main` had advanced, while `CHECKPOINT.json`,
`RELEASE_MANIFEST.json`, and the production-host installer still described Patch 038.

Earned changes:

- canonical release identity advances to `040-canonical-provenance-closure`;
- the exact Patch 039 merge commit is retained as provenance evidence;
- the macOS production installer now refuses a canonical source whose release identity is not Patch 040;
- the release metadata audit now compares the release identity with the highest numbered `README_PATCH_###.md`, so future numbered patches cannot silently outrun canonical metadata;
- no schema, governance, standing delegation, warrant, action boundary, classification authority, or production activation changes.

The governing rule is the same one Patch 039 enforced at runtime: a historical description may remain true without retaining jurisdiction over a changed present.
