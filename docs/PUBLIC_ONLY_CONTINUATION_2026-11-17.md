# Public-only continuation — 2026-11-17

Status: engineering operating boundary, **not** a product release, legal enactment, or downstream integration qualification.

## What stays active

- The already-public `FortCollinsBarber-netizen/StillPoint-Core-Canonical` remains the **single source-of-truth for new public Core work**. Its `main` history and approved successor policy remain intact.
- The existing Core and Apple Watch CI workflows remain the baseline. The additional `public-core-continuation.yml` workflow executes **only this public repository's own files**, through standard GitHub-hosted Ubuntu runners.
- The other existing public repositories remain available as separately identified historical or auxiliary sources. Do **not** silently infer that similarly named repositories are equivalent or authoritative.

## What stays private and paused for hosted qualification

The private RobertOS and StillPointOS implementations, private StillPoint material, and writing corpus retain their existing visibility, history, PRs, and source custody. Do not delete, expose, mirror, or reset them. Private-runner failure must not be misrepresented as Python test failure or used to force a merge. Resume downstream qualification only after a private execution route is demonstrably available or an independently authorized, publication-safe boundary is explicitly designed.

## Public CI safety boundary

1. Checkout only the public Core repository at the triggering commit; no cross-repository checkout.
2. Use Python standard tooling and in-repository tests, with `permissions: contents: read`.
3. Do not use secrets, private repository tokens, personal source archives, personal records, paid model calls, publishing credentials, or deployments.
4. A green public CI result proves **only the exact public Core commit and stated tests**. It must **never** be inherited by a private RobertOS or StillPointOS commit.
5. Keep fixed 364-day Common grid/52-week projection, the 2026–2075 finite publication boundary, protected civic vs. sacred-time distinction, independent Jubilee working profile, and no-grid-mutation safeguards under their established test/approval process.
6. Preserve visible distinctions among source custody, proposed working rule, software implementation, verification evidence, and real-world legal authority.
7. Do not modify billing or repository visibility as part of public Core development.

## Concrete first gate

The public continuation workflow installs this public repository with Python 3.11, executes the existing calendar-domain tests, selected temporal-authority tests, publication tests, and exercises the live public `calendar_day_payload` contract. It explicitly verifies the finite publication boundary: 2075 remains accessible; 2076 fails closed.

For release promotion, continue to require the separately declared authority and provenance gates; neither a smoke test nor a green Actions status grants a new operating policy automatically.

## Resume criteria for private integration

Only after an authorized test executor can obtain the **exact** private PR heads and execute their required tests with trusted provenance, preserve existing dependency order and verify the current Core pin. No private source copying into this public repository is permitted by this document. A separate explicit publication review is required before any public source extraction.
