# Patch 035 — Canonical Compatibility Closure

Purpose: repair integration seams revealed only by the first full Patch 008 + 009–032 canonical gate run on Python 3.13.

This patch does **not** broaden Signal authority, alter the CEO-approved governance digest, install approval evidence, inject credentials, or enable production sends.

Repairs:
- remove Patch 021 global `sys.modules` contract stubs that polluted the full unittest discovery process;
- preserve the real Patch 008 contract model (`ActionEvidence`, `ActionResult`, `ActionRequest.permitted`, positional `ArtifactRef`);
- make legacy Gmail event fixtures inherit the executor's exact configured account only when an event omits the account; an explicit mismatched account still fails closed;
- update pre-safety Patch 016 tests to the deterministic safety firewall semantics;
- make worker lease test clocks deterministic when `run_once(now_iso=...)` is explicitly injected;
- order equal-time lease events by append order (`rowid`) rather than random UUID;
- make schema tests assert the integrated/current schema rather than freezing a historical terminal version;
- update Patch 019 delegation test fixture for machine-enforced conditions;
- move the non-secret approved policy *draft fixture* into `tests/fixtures/` so Patch 032 tests are reproducible without publishing Patch 033 approval evidence.

First canonical run that motivated this closure: 420 tests, 3 failures, 28 errors. Most errors were cascades from the test-module pollution and missing test fixture.
