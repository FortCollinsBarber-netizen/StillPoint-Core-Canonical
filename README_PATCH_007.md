# Patch 007 — Bounded Production Outbox

Patch 007 is the first deliberately production-capable StillPoint external-effect boundary.

It adds exactly one new restricted action: `export_artifact`.

The `bounded_outbox` adapter:
- is disabled by default;
- requires `STILLPOINT_ENABLE_OUTBOX=1`;
- requires an explicit allowlist root in `STILLPOINT_OUTBOX_ROOT`;
- performs no network access;
- performs no email, publishing, payment, signing, deletion, or destructive operation;
- resolves one exact approved StillPoint artifact from durable runtime state;
- re-verifies the artifact SHA-256 immediately before the effect;
- rejects absolute paths, traversal, separators, symlink destinations, and path escape;
- writes through a temporary file + `fsync` + atomic `os.replace`;
- emits a durable JSON receipt with action/warrant/artifact/destination/result hashes;
- returns `ActionEvidence(type="export_receipt")` so completion remains evidence-gated;
- is idempotent for the same exact authorized action and fails closed on conflicting pre-existing output;
- remains subject to the existing warrant consumption, uncertain-dispatch, reconciliation, release, and re-entry machinery.

No production adapter is enabled merely by installing or importing StillPoint.
