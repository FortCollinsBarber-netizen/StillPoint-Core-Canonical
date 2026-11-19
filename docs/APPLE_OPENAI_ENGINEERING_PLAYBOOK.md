# StillPoint — Apple + OpenAI engineering playbook

Operational companion to Robert Emmanuel LaDay's November 18, 2026 Apple + OpenAI Engineering Reference, Edition 1.0. This is a condensed PUBLIC Core contributor guide, not a byte-for-byte copy of the private research packet or a replacement for current contracts. Check live documentation and source before implementing.

## Authority and product surfaces
* Canonical Core (this public repository) owns common calendar law, public read-only contracts and company action/warrant boundaries.
* Private RobertOS owns durable memory, provenance, context and the bounded Core bridge.
* Private StillPointOS owns operator/composition/qualification; observing newer code never creates execution warrants.
* Original writing and private source custody stay private; no private copying into public CI.
* Apple-first user experience: macOS, iOS, iPadOS, watchOS, Safari, and optionally iCloud/CloudKit. Public web remains standard accessible HTML/CSS/JS.
* OpenAI-only for NEW AI integrations. Legacy provider code is historical, not blanket authorization to run it. No third-party AI additions or paid OpenAI API calls without permission.

## Working engineering loop
1. Identify owner, repo, branch and exact commit; read established AGENTS, README, contracts and authoritative decisions.
2. Take one bounded task and implement it when authorized, not another vague planning cycle.
3. Build test fixtures from the canonical Core; never model calendar math by prompting an LLM or duplicating independent implementations in a client.
4. Run local tests first where possible; open a reviewable PR and inspect CI. Record failures accurately.
5. Before release verify Safari behavior and accessibility, actual distribution URL, real API responses, and (for watchOS) simulator and physical-device operation.
6. Capture work units, agent usage where available, and reproducible receipts. Do not start recurring engineering automations by default.

## Apple implementation standards
* Swift and SwiftUI first; separate model, View, async state and deterministic calendar contracts. Use AppKit only when needed.
* Xcode: record scheme, deployment target, simulator/runtime, signing, entitlements and test results. Test with Swift Testing / XCTest and device UI tests as relevant.
* Watch: inspect clients/apple-watch/CivicClock before rewriting it. WidgetKit complications are not a replaceable full third-party watch face. Consider offline snapshots, refresh budgets, low power and small displays.
* Validate timezone, location permission, DST versus fixed Common civil date, sunset calculations, VoiceOver, Dynamic Type and reduced motion.
* EventKit operations require permission and must not silently change civil-calendar events. App Intents require bounded scopes. CloudKit sync is opt-in with conflict/deletion design.
* Safari extensions need explicit permissions and documented APIs; never call undocumented ChatGPT history endpoints.

## Security and acceptance
* Secrets belong in authorized backends / secure local custody, not in web, apps, Watch binaries, GitHub commits or logs.
* Capability is not permission, and an approved request is not executed/completed until its exact result is verified and recorded.
* Preserve source-to-interpretation-to-current-authorized-version provenance. Historical manuscript language cannot silently regain runtime authority.
* Calendar civil grid: 364 days, 52 complete weeks; separate sacred, civic protected, astronomical and external overlay layers.
* Finite public publication 2026–2075; 2076 is calculation-only until individually authorized and qualified.
* Do not call private runner admission failure a failing test; check GitHub's actual job execution record.

## Official primary references
Apple: https://developer.apple.com/documentation/swiftui ; https://developer.apple.com/documentation/watchos-apps/ ; https://developer.apple.com/documentation/widgetkit ; https://developer.apple.com/documentation/appintents ; https://developer.apple.com/documentation/eventkit ; https://developer.apple.com/documentation/watchconnectivity ; https://developer.apple.com/documentation/safariservices/building-and-testing-a-safari-web-extension
OpenAI: https://developers.openai.com/learn/codex ; https://developers.openai.com/api/docs/guides/migrate-to-responses ; https://developers.openai.com/api/docs/guides/structured-outputs
Source: docs/STILLPOINT_TEMPORAL_ARCHITECTURE_AUTHOR_SELECTION_2026-11-17.md ; docs/PUBLIC_ONLY_ENGINEERING_LANE_2026-11-17.md ; clients/apple-watch/CivicClock/README.md
