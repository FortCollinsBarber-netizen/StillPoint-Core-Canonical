# StillPoint Engineering Handbook

**Edition:** 1.0 working · 2026-11-19  
**Authority:** Robert Emmanuel LaDay, final product authority  
**Home:** `StillPoint-Core-Canonical` / `docs/ENGINEERING_INSTRUCTIONS.md`  
**Machine/agent companion:** [`../AGENTS.md`](../AGENTS.md)  
**Other references:** [Apple/OpenAI Playbook](APPLE_OPENAI_ENGINEERING_PLAYBOOK.md), [Current Audit Status](ENGINEERING_AUDIT_STATUS_2026-11-19.md)  
**Type:** engineering development instructions; not a claim of production qualification, a new temporal selection, an enacted civil law, or an authorization to deploy.

This handbook turns the existing engineering reference and Canonical Core source into an actionable workflow for human developers, Codex and authorized AI engineering assistants. It **does not impose a blanket read-only rule**: engineering agents are expected to implement appropriate changes and produce executable evidence. It preserves the distinction between ordinary code development and consequential real-world actions.

## 1. What StillPoint is, and who owns what

StillPoint is the author's company operating system and Common Calendar project. AI providers are instruments, not the company or source of its authority.

| System | Scope | Not allowed to claim merely by existing |
| --- | --- | --- |
| **Canonical Core** (this public repository) | Authoritative Calendar contracts and published artifacts, company policies, durable warrants and action evidence, tests, web/Watch consumers | The full private company system is deployed or integrated |
| **RobertOS** (private) | Personal/corpus context, provenance, recovery and a bounded Core bridge | Permission to approve/exe­cute Core company actions |
| **StillPointOS** (private) | Operator composition, multi-system diagnostics and integration | Independent execution warrants or tested current-head production integration |
| **Writing corpus** (private) | Manuscript originals and source custody | Permission to publish, regenerate or rewrite original works |
| **Other retained repos** | Historical or supporting development and TAPE reference | Unilateral replacement of Canonical Core or transfer of authority |

Keep existing repositories and histories. A new repository, public mirror, or visibility change is not a substitute for fixing a test, dependency, access or workflow problem.

## 2. Source hierarchy and corrections

For a given change, identify the precise version and subject matter of each source. Prefer **the latest documented, explicitly author-selected, implemented and qualified working rule for that subject**; neither file modification time nor historical “LOCKED/CANONICAL” language alone determines active authority. Preserve historic documents and their original claims. Resolve contradictions openly.

Key source files:

1. [Dated temporal selection](STILLPOINT_TEMPORAL_ARCHITECTURE_AUTHOR_SELECTION_2026-11-17.md) — March 25 source anchor, 2027 epoch, overlap-49 selection, civil/sacred/observed-time distinctions and 2026–2075 finite publication.
2. [Calendar rule resolution](CALENDAR_RULE_RESOLUTION_2026-11-17.md), [cycle configuration](CALENDAR_CYCLE_CONFIGURATION.md), [ratification](CALENDAR_RATIFICATION_364.md) — mathematical rules and implementation context.
3. [Cross-system authority register](CROSS_SYSTEM_AUTHORITY_REGISTER_2026-11-17.md) — historical exact pins and qualification boundaries; **refresh current GitHub state before acting**.
4. [Public-only engineering lane](PUBLIC_ONLY_ENGINEERING_LANE_2026-11-17.md) — independently executable public Core tests and protected private source boundaries.
5. [Company policy](../policies/COMPANY.md) and [Core README](../README.md) — execution authority and installation/test conventions.
6. `RobertOS/AGENTS.md` in the **private** RobertOS repository — use there; this public handbook neither copies nor supersedes it.

The author also retained **StillPoint Apple + OpenAI Engineering Reference & GitHub Baseline Audit (2026-11-18)** in the ChatGPT Library. It is a historic engineering snapshot, useful for research and product direction; do not claim it is already synchronized into a repository or that its November 18 counts are still current.

## 3. Current temporal contract — implementation checklist

| Concern | Required present behavior | Test boundary |
| --- | --- | --- |
| Common civil calendar | 364 days; 52 complete weeks; stable weekdays | Every date and week, year-boundary checks |
| Source sacred overlay | Four 30/30/31 quarters; Month I/Day 1 = Common March 25 / Wednesday | Source-to-civil mapping parity and provenance |
| Jubilee | 2027 Cycle 1 Year 1; 49-year overlapping rollover; 2076 calculated proclamation | 2075 last Cycle 1 year; 2076 Cycle 2/Year 1; standalone-50 remains explicitly comparison-only |
| Publication | **2026 through 2075 inclusive** | Return clear failure for unpublished 2076 requests; no fabricated payload |
| Civic protected time | Friday civil dusk through Sunday civil dawn | Distinguish from sacred sunset and device/timezone inputs |
| Sacred observance | Separate sunset-based interpretation with source attribution | No silent interchange with civic intervals |
| Client parity | Versioned Core API, validated exports, web/Watch resources | Exact published hashes, schema and representative date vectors |
| Civil legal effects | None inferred from calendar calculation alone | No generated debt/property/release actions |

The nine functional responsibilities are Common Calendar, Civil Clock, Civic StillPoint, Civic Holidays, Sacred/Religious Time, Sun/Season/Local Light, Lunar Layer, Long Cycles, and External Translation. A calculator may present these layers together; it must not silently merge their authority or overwrite unrelated people's calendars.

The current working model can be modified by a **later specific author decision**, with migration, source/consumer reconciliations, regenerated resources, tests, and preserved prior evidence. That is controlled development, not forbidden change.

## 4. The standard engineering work order

For each issue or user instruction, produce a small **work-order record**, even if only in the PR description:

| Field | Record |
| --- | --- |
| Outcome | What observable working behavior should change? |
| Jurisdiction | Core, RobertOS, StillPointOS, web, Watch, manuscript or external system |
| Source/decision | Exact document/contract and version; contested assumptions |
| Baseline | Repo, branch, full head SHA, current files, current tests/CI |
| Change | Bounded file edits and migration/contract implications |
| Safety | Private-data exposure, authority boundaries, permission and approval implications |
| Evidence | Tests actually run, commit and artifact hashes, screenshots/device results if applicable |
| Release decision | Proposed/merged/published/verified; remaining separate gates |

**Default action:** Implement the request in the existing correct repository. Prefer a branch + PR and regression tests. Do not simply re-audit the same baseline or tell the inventor the system cannot develop because a prior audit was read-only.

**Stop conditions:** Unknown authority over a consequential action, request requiring private source on a public branch, unverifiable calendar change, insecure secret exposure, missing exact approval for spending/publishing, or failing required acceptance. Stop that action, not unrelated safely authorized coding.

## 5. Local commands and test matrix

Prerequisite: Python 3.11+ and the repository's checked-out source; install from source when practical.

```sh
python -m pip install .
python -m unittest discover -s tests -q
python -m unittest discover -s tests/calendar_core -p 'test_public_consumer_conformance.py' -v
python -m unittest discover -s tests/public_core -p 'test_*.py' -v
python eval/run_eval.py
python eval/run_calibrated.py
python eval/run_shadow.py
```

Run the tests relevant to the actual change. Do not mutate frozen evaluation corpora to force a pass. The scripts above are **runbook commands, not test results**. If network, local checkout, Apple toolchain or GitHub runner access is unavailable, explicitly state which checks were **not run**.

Expected evidence by change type:

| Change type | Minimum evidence in addition to reviewed diff |
| --- | --- |
| Calendar logic/export | Deterministic geometry and rollover vectors; exact golden export comparison; boundary and out-of-publication failures |
| Public assistant/API | Valid/invalid schema inputs; read-only/no company-state side effects; current version match; denial cases |
| Company authority or adapter | Denied/stale/compound approval tests, exact destination binding, idempotency, durable receipts, real completion criteria |
| Persistence/migrations | Upgrade from prior state, replay/recovery, isolation, custody and no data-loss regressions |
| Web interface | Keyboard/focus, accessibility, Safari, public schema and time-boundary checks; independent hosted browser verification to claim live acceptance |
| Watch/Apple | Shared resource parity, `swift test` when available, simulator build, permissions, offline/locale/twilight tests, physical device before “device verified” |
| Cross-repository | Exact pinned Core/RobertOS/StillPointOS source; combined tests; no authority inheritance or private-source leak; independently executed downstream CI |

A public CI success establishes only what that job actually tested. A private CI run with no runner and no steps has not executed the test suite and must not be reported as a test failure. A successful PR merge does not equal installed/released user functionality.

## 6. AI, Apple and external integrations

**Current direction:** Apple-first product surfaces; OpenAI is the only approved **new** AI integration. Keep calendar and custody deterministic/provider-independent. Legacy provider support in code is historical evidence, not permission to activate or pay for it. An actual model/API deployment needs separately authorized credentials, budget, operational logs and privacy review.

**Apple work:** The existing Watch source is in `clients/apple-watch/CivicClock/`; inspect before replacing. A Watch app, complication, website, Safari extension and full native Mac/iPhone/iPad app are different capabilities with different testing and signing requirements. Do not assert any are installed merely because source exists. Use appropriate Apple permissions for EventKit, location and CloudKit. Keep secrets in authorized backend/Keychain scope, not in a web bundle or public extension.

**External actions:** Every proposed action must validate its target and authority. Preserve `ActionRequest` state, approved artifact hash/identity, adapter execution, outcome and proof. For changes to personal data, mailboxes, publishing, payments or external accounts, a developer's ability to write code is not the user's approval to execute.

## 7. Release and qualification ladder

Use the following labels exactly to avoid misleading the user:

1. **INVENTORIED** — file/entry found.
2. **SOURCE-INSPECTED** — specific content read.
3. **CI-PASSED** — particular job passed against particular SHA.
4. **LOCALLY TESTED** — exact commands executed in a documented environment.
5. **BROWSER/DEVICE VERIFIED** — real external page/device behavior independently operated.
6. **CROSS-SYSTEM QUALIFIED** — exact pins and joint behavioral/authority tests passed together.
7. **RELEASED** — actual distribution/deployment verified and approved within scope.

Do not roll these up into a single “green.” Maintain blockers with precise reproduction, owner/affected subsystem and next verifiable action. When a user has authorized a particular launch, carry it through and verify it; when the instruction is only to build internal engineering documentation, a **proposed PR** is the correct deliverable rather than an unrequested production deployment.

## 8. PR checklist

- [ ] I read current source and authority, verified branch/commit and checked for an existing implementation.
- [ ] The change has one identified technical outcome and does not create redundant repositories or duplicate Calendar authority.
- [ ] No original manuscript, private source, Git history, generated output or migration has been silently overwritten.
- [ ] The implementation is consistent with the selected calendar and publication limits, or the author explicitly selected a documented successor.
- [ ] New behavior includes positive, boundary and deny/error tests.
- [ ] Tool permissions, action receipts, privacy and secrets were reviewed.
- [ ] I ran appropriate tests and gave exact results and skipped/unavailable checks.
- [ ] I distinguished PR, merge, CI, deployment, user-facing acceptance and cross-system qualification.
- [ ] I documented open blocks and the next executable action without inventing results.

---

**Maintenance rule:** Update these instructions through reviewable changes when there is an authorized technical decision. Keep dated versions and cite the new governing source. This handbook is meant to make the engineering work **happen** while keeping the work traceable.
