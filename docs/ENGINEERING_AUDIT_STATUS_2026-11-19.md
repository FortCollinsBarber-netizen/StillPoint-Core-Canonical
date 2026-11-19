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
