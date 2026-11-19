# StillPoint engineering audit — working evidence register

Date: November 19, 2026. Purpose: make the backlog actionable, not claim unearned full qualification. This document is a dated checkpoint. Current repository refs and CI must be checked again for future releases.

## Verified inventory as of audit baseline
Eight distinct GitHub repositories, 919 tracked files across them, 656 with a broad code/configuration-extension filter (not a lines-reviewed count). Canonical Core current main 86db478bb1e1af9239be839d38f4c51e63387501 contained 457 files and 336 broad code/config files. RobertOS current main 7a93e19eda21dee2578905563637fcdd82f4aeb8: 150 files. StillPointOS current main ad17564572a0f9587ac9c820d30133f99244026a: 141 files. These are inventories, not a semantic all-line audit.

## Findings and next acceptance gates
A1 / HIGH / OPEN — Private runner admission: RobertOS GitHub Actions run 44122391109 and StillPointOS run 44122484973 reported failure with no assigned runner and no executed steps. Establish the GitHub-side admission reason; separately execute private component tests where possible. Do not represent as executed test failure.

A2 / HIGH / OPEN — Cross-system: RobertOS, Canonical Core and StillPointOS lack current exact-head integrated CI qualification. Preserve separate company/action, memory and operator authorities. Never infer production readiness from individually passing public Core.

A3 / HIGH / OPEN — Calendar boundary: validate published 2026–2075 artifacts, 2076 exclusion, March 25 sacred coordinates, 2027 overlap-49 Jubilee, separate civic/sacred/sunset observances, and client parity using existing tests/fixtures.

A4 / MEDIUM / OPEN — Apple Watch: CivicClock Swift/SwiftUI, WidgetKit, test files and publication resources exist. Test supported Xcode/watchOS simulator and real device; check entitlements, location, offline behavior and documentation drift. SOURCE EXISTS does not mean DEVICE VERIFIED.

A5 / MEDIUM / OPEN — Website: site/stillpoint-calendar/index.html is a sizeable single HTML/CSS/JS page. Review accessibility, Safari, content structure, exports and design before implementing a new visual system; never replace calendar law inside web code. Pages workflow completed deploy steps on main, but independently verify served URL and data before release assertion.

A6 / HIGH / OPEN — External actions/secrets: source includes warrant handling, secret custody, Gmail and iCloud Mail adapters and historical xAI provider modules. Verify exact authorization, env switches, credential handling, input validation, idempotency and dispatch receipts before enabling any production action. Presence does not prove enablement.

A7 / HIGH / OPEN — Review debt: StillPointOS had 90 open draft pull requests at the inspected query. Classify ownership, overlapping changes, base lineage, tests and disposition. Avoid bulk merge or deletion. Canonical Core had PRs #78 and #79 as drafts.

A8 / MEDIUM / IN PROGRESS — Reproducible file coverage: tools/audit_source_inventory.py records tracked files and local hashes/line counts while correctly labeling them NOT_READ. A reviewer must separately mark files SOURCE_INSPECTED / TESTED with file:line evidence. Do not claim the manifest equals a security review.

## Evidence rules
INVENTORIED = path/blob exists; SOURCE_INSPECTED = contents reviewed; CI_PASSED = a precise job on a precise SHA; LOCALLY_TESTED = command executed locally; BROWSER_OR_DEVICE_VERIFIED = interface operated; CROSS_SYSTEM_QUALIFIED = selected pins/permissions verified together; RELEASED = independently accepted distribution.

No PR in this checkpoint merges itself. Do not publish private source, add service charges or start recurring development schedules. This register is public-safe; private evidence remains in its own repository.

## November 19 execution checkpoint (subsequent to abf49b3)

**Audit scope / no overclaim:** Canonical Core main `abf49b3dd7dba40d91a376c3490b069a011f8ec7` is the pinned baseline. This checkpoint records selected exact-file review, not a semantic review of all eight repositories or all 919 historically inventoried files. The source inventory's `NOT_READ` default remains authoritative until separately supported inspection evidence is recorded. Changes below are reviewable PRs, not yet merged or released.

**SEC-01 / HIGH / CONFIRMED SOURCE GAP / PR #116:** `stillpoint/runtime.py:569-720` earlier validates time and artifact authority; `stillpoint/db.py:940-947` accepted a warrant marked active without independently validating its current `valid_from`/`valid_to` under the final durable dispatch transaction. A prechecked warrant could expire before dispatch. Proposed transaction-level revalidation and rowcount correction: `https://github.com/FortCollinsBarber-netizen/StillPoint-Core-Canonical/pull/116`. Added expired-interval and future-start regression cases in `tests/test_durable_dispatch_integration.py`. Initial CI exposed an invalid expired test fixture (database correctly enforced `valid_to > valid_from`); fixture corrected. Final proposed head `d3b6c6e2bdfb238444b892613aa9394a8c73c0ca`: full Core CI PASS, runs `44490447005` (PR) and `44490437897` (push). Production effect NOT TESTED.

**WATCH-01 / MEDIUM / CONFIRMED SOURCE GAP / PR #117:** `clients/apple-watch/CivicClock/WatchApp/LocationService.swift:39-125` originally started unbounded best-accuracy location updates until Ground Zero lock and had no explicit stop on inactive scene, permission loss or Core Location errors. Proposed 60-second attempt limit, lifecycle stop, stale-callback guard and retry display, without rewriting immutable Ground Zero: `https://github.com/FortCollinsBarber-netizen/StillPoint-Core-Canonical/pull/117`. Proposed head `02c17e01de931adadb8df6d311fdaf03a9d8738f`: native Watch CI PASS runs `44490854666` and `44490800995`; Core CI PASS runs `44490854639` and `44490801037`. This is simulator build and Swift-test evidence, **not physical Watch battery/device qualification**.

**PRIVATE-01 / HIGH / BLOCKED:** RobertOS main `7a93e19eda21dee2578905563637fcdd82f4aeb8`; StillPointOS main `ad17564572a0f9587ac9c820d30133f99244026a`. Their relevant private GitHub jobs (`44122391109`, `44122484973`) failed with no runner and zero executed steps; cause unconfirmed. RobertOS PR #123 and StillPointOS PR #158 are merged; StillPointOS's `SYSTEM_MANIFEST.json`, `contracts/calendar.json` and selected-source snapshot retain exact version pins. The selected Core candidate pin is earlier than the current public documentation-only successors, which is not in itself a defect. No current-head private multi-repository qualification has passed.

**SITE-01 / OPEN:** Live external fetch of the GitHub Pages URL and `/data/index.json` could not be completed through the available browser. GitHub Pages workflow status is separate from remote acceptance. Do not claim a fresh HTTP 200 or keyboard/Safari usability verification from this session.

### Files actually inspected in this execution session

| Repository and evidence level | Exact source scope reviewed |
| --- | --- |
| Core / SOURCE_INSPECTED (targeted) | `stillpoint/db.py:781-1013,1730-1804`; `stillpoint/runtime.py:530-725`; `stillpoint/temporal/action_gate.py:1-150`; `stillpoint/temporal/warrants.py:120-224`; `stillpoint/authority/delegated_warrants.py:1-330`; `stillpoint/adapters/registry.py:1-108`; `stillpoint/adapters/gmail_send.py:1-337`; `stillpoint/secret_custody.py:1-54` |
| Core / TEST_INSPECTED + exact-head CI | `tests/test_durable_dispatch_integration.py` (targeted test methods), `tests/test_mandatory_action_warrant.py`, `tests/test_patch017_dispatch_revalidation.py`; PR #116 above |
| Watch / SOURCE_INSPECTED + exact-head CI | `WatchApp/LocationService.swift`, `WatchApp/CivicClockApp.swift`, `WatchApp/CivicClockView.swift`, `Shared/GroundZeroObservation.swift`, `Shared/GroundZeroSamplingPolicy.swift` (new), `Tests/ClockGroundZeroAndLunarTests.swift`, `Package.swift`, `project.yml`, `README.md`, `.github/workflows/apple-watch.yml`; PR #117 above |
| StillPointOS (private) / SOURCE_INSPECTED selected records | `SYSTEM_MANIFEST.json`, `contracts/calendar.json`, `contracts/feature_matrix.json`, `qualification/robertos_selected/SNAPSHOT.json`, `qualification/robertos_pin/SNAPSHOT.json`, `docs/CHECKPOINT004_CROSS_SYSTEM_AUTHORITY_2026-11-17.md`; no full execution |
| All other repository files | INVENTORIED only, or **NOT_READ** by this checkpoint. No 919-file semantic review claimed. |

**Next executable gate:** independent review of PR #116 and #117; then exact merged-main CI and, for Watch, physical-device measurement. Continue Core approval-to-dispatch threat inspection, downstream pin/test reconciliation and website browser acceptance. Recurring engineering automations remain disabled. No secrets or private contents are copied into this public register.

## Integration closure — 2026-11-19 (supersedes earlier "proposed" statuses)

The entry above captures the earlier review checkpoint; these later dispositions are authoritative. **No code or source evidence has been deleted.**

| Correction / severity | Reviewed exact PR head | Squash merge on main | Evidence |
| --- | --- | --- | --- |
| SEC-01 / HIGH / corrected, not production-qualified — [PR #116](https://github.com/FortCollinsBarber-netizen/StillPoint-Core-Canonical/pull/116) | `f4752308a84f5de175335ab9a5fcc718488ac05a` | `b109cc66d4aa9c1c0913ad3d4c69d792b281a050` | [Core PR CI 44491511143](https://github.com/FortCollinsBarber-netizen/StillPoint-Core-Canonical/actions/runs/44491511143): 7/7; [merged-main Core CI 44493601895](https://github.com/FortCollinsBarber-netizen/StillPoint-Core-Canonical/actions/runs/44493601895): success |
| SEC-02 / HIGH / corrected, not production-qualified — [PR #118](https://github.com/FortCollinsBarber-netizen/StillPoint-Core-Canonical/pull/118) | `4595fe9c8b20ed3e9f33fdb9567c451f223bf82f` | `ea99b3cb0c25af71a6d05215dc3bb3041e62fdc4` | [Core PR CI 44493692582](https://github.com/FortCollinsBarber-netizen/StillPoint-Core-Canonical/actions/runs/44493692582): 7/7; real partial-pipe timeout regression; merged-main Core CI 44494311742: success |
| WATCH-01 / MEDIUM / corrected, device not yet qualified — [PR #117](https://github.com/FortCollinsBarber-netizen/StillPoint-Core-Canonical/pull/117) | `5605a315707e531ec16643339f590be7a87ffb02` (two-parent branch reconciliation preserved earlier head `28473d5507d2ca91e7d2d36ffeef9306e24274d8`) | `87da21c703b8cdce57ab0601ce8f0819377ceb1c` | Combined-head PR Core CI 44494626669 7/7 and Watch CI 44494626681 PASS; [final merged-main Core CI 44495012680](https://github.com/FortCollinsBarber-netizen/StillPoint-Core-Canonical/actions/runs/44495012680) 7/7; [final merged-main Watch CI 44495012778](https://github.com/FortCollinsBarber-netizen/StillPoint-Core-Canonical/actions/runs/44495012778) PASS |

**SEC-01 accepted boundary:** the finite warrant's true UTC validity and current status are verified inside the final durable-dispatch transaction; failed checks roll back before creating a dispatch row or consuming a warrant. Any external adapter effect after the committed boundary remains a separate evidence/reconciliation stage, not evidence of human-visible completion.

**SEC-02 accepted boundary:** FD secret reads use a monotonic global read deadline, bounded 64 KiB buffering, typed failure, FD closure and no fallback following specified FD failure. The real-pipe test writes partial credential bytes and intentionally leaves the writer open, exercising the OS-level stall. Legacy env fallback is still only invoked when the FD variable is absent or empty. Existing macOS Keychain/FD launch scripts were source-inspected; production credential access was not exercised.

**WATCH-01 accepted boundary:** initial high-accuracy Ground Zero capture has 60-second bounded attempts, permission/failure/background stop behavior, explicit foreground retry, and immutable saved observation. Further premerge review separated `stopSampling()` from scene-inactive `stop()` and provided a user-controlled retry. Swift/package tests and macOS watchsimulator build are PASS; real-device lifecycle, GPS power, and distribution have NOT been tested.

**Combined-main qualification:** Canonical Core `87da21c703b8cdce57ab0601ce8f0819377ceb1c` has seven independently successful jobs and Apple Watch `calendar-client` successful with shared-law export diff, 50-year publication identity, native Swift tests, XcodeGen and WidgetKit simulator build. Calendar's 2026–2075 publication boundary remains intact; this does not authorize 2076 publication.

**Private boundaries:** RobertOS and StillPointOS remain private and are not current-head integrated/production-qualified. The existing private StillPointOS [runner-admission issue #151](https://github.com/RobertEmmanuelLaDay/StillPointOS/issues/151) documents pre-job failures with zero steps and inaccessible startup annotations; billing is NOT established as the cause. A separate private authorization investigation is tracked as [StillPointOS #160](https://github.com/RobertEmmanuelLaDay/StillPointOS/issues/160); do not place private source or sensitive attribution details here. No hosted private tests have been relabeled as passing.

**Coverage disposition:** target-reviewed Core authority, SQLite dispatch, credential custody, Watch location/client, selected RobertOS and StillPointOS authority/bridge files and contract pins. The eight-repository 919-file historical inventory is **not a semantic audit**, and unexamined files remain NOT_READ. Remaining qualification: host/operator identity, private cross-system tests, public website browser/mobile accessibility, real-device Watch and production adapters. Preserve prior audit statuses as historical evidence; merged source is not automatically deployed.

**Next executable inspection:** StillPointOS's private CLI-to-Core caller-origin trust boundary, especially the difference between asserted operator name and independently authenticated origin, alongside Core's direct CLI access controls and real host ACLs. No recurring engineering schedules have been created or restarted.
