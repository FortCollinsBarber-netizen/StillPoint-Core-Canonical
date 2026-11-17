# Checkpoint 004 — Resumption Verification and Remaining CI Hold

**Original author and principal investigator:** Robert Emmanuel LaDay  
**Date:** November 17, 2026  
**Scope:** Finish the existing selected calendar implementation, reconcile its actual consumers, preserve authorial provenance, and distinguish local execution from hosted CI and deployment.

## The selected Core implementation is merged

[Core PR #83](https://github.com/FortCollinsBarber-netizen/StillPoint-Core-Canonical/pull/83) merged at `ecbddbed31d38770b8c1b3e67fb8aad5a6a0ec1c`. [PR #84](https://github.com/FortCollinsBarber-netizen/StillPoint-Core-Canonical/pull/84) merged at `90896d71faa11ceb69106434d459f0b25fe56e41`, preventing explicit comparison inputs from inheriting selected operating authority. This is the exact engine pin used in the coupled verification.

Both selected policy records use `author-selected-working-rule-not-civil-enactment`, identify `Robert Emmanuel LaDay`, and record `2026-11-17`. The working sacred anchor is Common March 25; the independent Jubilee epoch is 2027; rollover is `overlap-49`. Common 2075 is Cycle 1 Year 49. Mathematical 2076 is Cycle 2 Year 1 and the first ordinal-fiftieth proclamation, followed by 2125, 2174, 2223, 2272 and 2321. Arithmetic does not publish those later dates or execute legal release.

The [Authorial Selection and Ratification Addendum](STILLPOINT_TEMPORAL_ARCHITECTURE_AUTHOR_SELECTION_2026-11-17.md) preserves the September manuscript's earlier unresolved status, enumerates all nine functional layers, names the companion manuscripts and records why the modern selection is accountable and supersedable. Earlier source versions remain historical evidence. None acquires perpetual operative authority through the words locked, frozen or canonical.

The current 364-date civil grid remains selected; it is not immune from an authorized verified successor. Civic protection remains Friday civil dusk through Sunday civil dawn, independently of sacred sunset observance. Good Friday and Easter are not restored as perpetual April 3/5 assignments. The finite publication remains 2026–2075 and rejects runtime requests for 2076 even though the selected mathematical model can calculate its position.

## Recovered defects and concrete corrections

The saved changes were recovered after the interrupted session. Current GitHub main and the earlier merges were refreshed before proceeding; no original manuscript or other worker's source was overwritten.

RobertOS's Clock v2 selection had been merged, but `robertos/company.py` still required the historical `stillpoint.calendar-day.v1` response. Its matching old mock passed while actual selected-Core reads failed. [RobertOS PR #123](https://github.com/RobertEmmanuelLaDay/RobertOS/pull/123) requires v2 and validates the selected author/date, March 25 anchor, 2027 epoch, overlap-49 rollover, distinct civic twilight and finite map. Explicit comparison inputs cannot replace that default. The real subprocess verifier now checks 2075 Year 49 and rejects unpublished 2076. The CI matrix invokes that verifier against exact pinned Core. `AGENTS.md` now distinguishes source custody from supersedable operating authority and prohibits backward compatibility from silently retaining superseded working rules.

StillPointOS's facade expected coverage in `publication`; actual Core v2 reports it under `map`. [StillPointOS PR #158](https://github.com/RobertEmmanuelLaDay/StillPointOS/pull/158) corrects both the validator and the fixture and tests that fabricated publication metadata cannot hide an expanded map. Its active candidate manifest, lock, feature matrix, provenance and README select the corrected RobertOS `0bc724a11c49797e7371aa035ef1c984ed70c257`. Both qualification lanes install an exact-blob selected-source snapshot and run its actual verifier. The older RobertOS snapshot remains unchanged historical evidence, is no longer the candidate runtime, and is not shipped in the wheel. The selected snapshot is also qualification-only and excluded from the package. No additional runtime, calendar engine or repository was created.

## Actual verification evidence

| Verification | Observed result and scope |
|---|---|
| Core runtime unit/integration suite | 723 tests passed locally on the exact selected engine checkout. |
| Core calendar-domain suite | 150 tests passed locally. |
| Explicit authority, recovery, interruption and continuity regressions | 86 tests plus four subtests passed locally; this lane overlaps some full-suite coverage and is not an additive unique-test count. |
| RobertOS canonical release gates | 278 tests per run, behavioral/review verification and fresh-install checks passed on Python 3.11.18, 3.12.14 and 3.13.5 in separate clean worktrees. The uploaded tree exactly matches the tested tree. |
| RobertOS real Core bridge | Passed on all three Python versions, including read-only behavior, transactional continuity, selection provenance and 2075/2076 boundaries. All test state was isolated. |
| StillPointOS tests | 78 passed on each of Python 3.11, 3.12 and 3.13. |
| Actual coupled routes | Exact RobertOS candidate Git pin and Core pin verified; selected Clock status, calendar facade, governor, civil clock and Watch compatibility passed. |
| Existing workflow steps executed locally | Nine distinct provenance, historical/selected snapshot, live bridge, facade, packaging and clean-install checks passed. The first isolated packaging attempt lacked pip; after installing pip in that scratch environment, the unchanged packaging steps passed. |
| Shared exports | Existing exporter regenerated spec, vectors, population and manifest; all four were byte-identical to retained Core artifacts. Watch/Core byte-identity checks passed. |
| Native Apple Watch | PR #83 head `942fb45ecf065e76df96cf3fe62bd55c24c14ceb`, Actions job `134003352590`: shared-resource regeneration, native Watch projection tests, Xcode project generation and watchOS app/WidgetKit build all completed successfully. PR #84 also has a successful subsequent `calendar-client` run. No physical-device installation is claimed. |
| Core main hosted CI before this documentation successor | All seven checks passed at `51adab6af40c22a071616ab47e77b4ee3373cdc2`, run `44080387991`. This documentation successor needs its own current-head checks before merge. |

The first simultaneous local packaging attempt shared a build directory across Python versions and collided. Those attempts were replaced with successful isolated-worktree gates; the failed attempt is not counted as a pass. No code change was needed to repair the test environment. The local gate's commit metadata differs from the connector-created commit metadata, while the full Git tree is identical; this is reported as tree-equivalent local evidence, not an invented hosted exact-head run.

## Exact candidate identities and the unresolved hosted gate

| Repository | Current correction head | Source tree | Hosted result |
|---|---|---|---|
| RobertOS, PR #123 | `0bc724a11c49797e7371aa035ef1c984ed70c257` | `d7388f3c4138400e88e16bf9537529ad3911bcea` | Run `44085648061`: three failed jobs, no executable steps. |
| StillPointOS, PR #158 | `2174566199c3bf6b83dd839e147ec280edb153e1` | `8eae80ded18e197fb30fb9beccc7c69b862c9c8e` | Run `44087157998`: seven failed jobs, no executable steps. The separate successor workflow likewise did not qualify. |

GitHub's reported job failures precede test execution. The connector evidence does not establish the account-level cause, and this record does not infer unpaid billing or modify budgets, credentials, runner permissions or deployment settings. Passing local tests does not convert those hosted jobs into successful runs.

Both correction PRs remain open, ready for review and **unmerged**. No anchor decision or further correction authorization is needed. The precise continuation is to restore executable private Actions jobs, rerun required qualification on these heads or a carefully reconciled successor, merge RobertOS #123 first and StillPointOS #158 afterward when their gates pass, verify the resulting main branches and update the authority register. The candidate RobertOS pin already identifies the corrected immutable source commit; a merge is not permission to replace it with an untested moving head.

The source-critical research, future civil enactment, any 2076 publication extension, physical Watch installation, service deployment and public release remain separate work. No Firebase database, paid external call or new cloud resource was created.
