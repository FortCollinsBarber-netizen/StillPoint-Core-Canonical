# StillPoint Core Patch 001 — Temporal Authority Fail-Closed Hardening

This bundle is a **post-materialization repair patch**, not a replacement for the full Core tree.

It addresses the independent audit findings:
- unknown warrant status failing open to ACTIVE
- malformed warrant dates silently broadening authority
- finite-warrant enforcement
- subject/target/scope containment
- sensitive cross-domain promotion
- unknown/malformed claim temporal state
- evidence immutability/hash/confidence validation
- release strict boolean parsing and exact warrant/subject binding
- forward-only schema hardening in migration 006

## Files
- `stillpoint/temporal/claims.py`
- `stillpoint/temporal/warrants.py`
- `stillpoint/temporal/evidence.py`
- `stillpoint/temporal/firewall.py`
- `stillpoint/temporal/reentry.py`
- `migrations/006_temporal_authority_hardening.sql`
- `tests/test_temporal_hardening.py`

## Important
1. Materialize/prove the exact earned `6fdfa67` tree first.
2. Do not rewrite migration 005.
3. Apply this as a new repair commit after the provenance checkpoint.
4. Mirror migration 006 under `stillpoint/migrations/`.
5. Then wire the runtime ActionRequest boundary to mandatory warrants and add DB warrant APIs.
