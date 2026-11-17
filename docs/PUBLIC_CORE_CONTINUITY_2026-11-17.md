# StillPoint public-core continuity — November 17, 2026

**Working decision:** Continue engineering in the already-public and currently executable [StillPoint Core Canonical](https://github.com/FortCollinsBarber-netizen/StillPoint-Core-Canonical). Keep the private downstream repositories and their histories intact while their GitHub-hosted jobs are rejected before execution. This is an **engineering continuity route**, not a transfer, replacement of authority, release certification, or instruction to disclose private materials.

## Repository boundaries (both GitHub accounts)

| Repository | Visibility | Engineering disposition |
|---|---|---|
| `FortCollinsBarber-netizen/StillPoint-Core-Canonical` | Public | Authoritative public Core source; continue building, testing and reviewing changes here. |
| `RobertEmmanuelLaDay/StillPoint-` | Public | Independent earlier finite-warrant runtime. Its passing tests are useful evidence, not a substitute for current Core or a coupled qualification. |
| `RobertEmmanuelLaDay/StillPoint-Core` | Public | Historical export, not the active Core source. Preserve. |
| `FortCollinsBarber-netizen/the-tape-protocol` | Public | Separate public protocol; no automatic calendar authority. |
| `RobertEmmanuelLaDay/RobertOS` | Private | Preserve code, PR #123 and commit `0bc724a11c49797e7371aa035ef1c984ed70c257`; no public copying or release promotion. |
| `RobertEmmanuelLaDay/StillPointOS` | Private | Preserve code, PR #158 and commit `2174566199c3bf6b83dd839e147ec280edb153e1`; no public copying or release promotion. |
| `RobertEmmanuelLaDay/StillPoint` | Private | Historical source; preserve privately. |
| `RobertEmmanuelLaDay/writing-corpus` | Private | Manuscript custody; preserve privately. |

## Demonstrated runner distinction

On November 17, [Canonical Core run 44088514711](https://github.com/FortCollinsBarber-netizen/StillPoint-Core-Canonical/actions/runs/44088514711) passed seven real, executed jobs, including Python 3.11/3.13, calendar package, export checks, and publication validation. [Public StillPoint- run 44078066616](https://github.com/RobertEmmanuelLaDay/StillPoint-/actions/runs/44078066616) passed its two Python jobs. Conversely, [private StillPointOS run 44087157998](https://github.com/RobertEmmanuelLaDay/StillPointOS/actions/runs/44087157998) and [private RobertOS run 44085648061](https://github.com/RobertEmmanuelLaDay/RobertOS/actions/runs/44085648061) recorded failures with zero executed steps. That is a **runner-admission problem** on the private side, not evidence of failing Python tests. Billing/exhausted allowance remains an unverified possible cause.

The [Public Core Continuity workflow](../.github/workflows/public-core-continuity.yml) is a minimal, additive public-only qualification lane. It checks out **only this public repository**, installs its package, runs its calendar-domain and finite-publication tests in Python 3.11 and 3.13, and explicitly checks the published 2026–2075 range. It does not fetch private repositories or require provider tokens, payment, or private GitHub Actions compute. Main Core CI and its existing gates remain intact.

## What stays separate

- Current calendar/clock working selection: March 25 sacred source-year anchor; 2027 Jubilee epoch; overlapping 49-year cycles; independent 364-day civil grid; Friday civil dusk to Sunday civil dawn protection; finite publication 2026–2075. A mathematical 2076 position is **not** a published 2076.
- The independent public-only workflow validates **public Core**, not the live RobertOS + StillPointOS integration. Their private correction candidates stay intact and unmerged until independent exact-head testing can execute on an appropriately private runner.
- Do not copy private repository source, source vaults, personal writing, credentials, user data, historical Actions logs, or unreviewed artifacts into any public repository or workflow.
- No GitHub billing updates, visibility flips, destructive migration, new paid infrastructure, or production deployment are part of this route.

**Progression rule:** Develop reviewed public Core code in normal branches/PRs, prove actual executed jobs on public standard runners, and maintain the existing source/version evidence. Only publish a downstream component when its actual contents **and Git history** are audited and a separate release decision exists. The existing private issue [StillPointOS #151](https://github.com/RobertEmmanuelLaDay/StillPointOS/issues/151) remains the diagnostic record; this document does not weaken any cross-system qualification gate.
