# StillPoint Calendar Core — Executable Domain Contract

stillpoint.calendar_core is the platform-neutral temporal-geometry and calendar-domain engine. It is deliberately separate from stillpoint.temporal, which owns temporal-authority and continuing-evidence semantics.

## Architectural split

Calendar Core exposes three different machine surfaces:

1. calendar_core_spec.json — stable machine-readable calendar law.
2. A finite calendar publication — explicit enactment/evidence input whose authority expires at its published range.
3. calendar_projection_vectors.json — conformance-only proof data for native clients. Test fixtures do not acquire civic authority.

The historical calendar_core_contract.json remains a compatibility bridge for the stacked Apple/Jubilee branch. New consumers should not treat that bridge as a constitution.

## Domain jurisdictions

Continuous time: K = 0,1,2,... across adopted dusk boundaries. It does not gap.

Ordinary annual time: Y_n-001 through Y_n-364. Month, quarter, phase, gate, and ordinary day-of-year live only here.

Reconciliation: Y_n/Y_n+1-R1 through R7 when R_n=7. Reconciliation is interannual. It inherits no month, quarter, phase, gate, or ordinary day-of-year.

## Public surface

- apparent_sunrise_utc / apparent_sunset_utc
- bracket_sunset
- phase_for_base_day
- protected_time_state
- select_v32_nearest_legal
- select_v33_nearest_spring_gate
- project_dual_stamp
- jubilee_state
- get_calendar_snapshot
- build_calendar_core_spec
- build_calendar_projection_vectors
- validate_publication_rows

## Weekly rule

Sabbath: Friday apparent sunset through Saturday apparent sunset.
Lord's Day: Saturday apparent sunset through Sunday apparent sunset.
StillPoint: Friday apparent sunset through Sunday apparent sunrise.

## Annual custody

Recovered v3.2 remains callable under its own version. The current v3.3 successor candidate uses 364 ordinary days, then 0 or 7 interannual Reconciliation days, then the next ordinary year. Its current candidate Spring Gate is Common Month 3 Day 20, ordinal 80.

The publication compiler consumes explicit epoch/reference/evidence inputs. Calendar Core does not ratify those inputs merely because it can calculate with them.

## Six paired gates

Gate sequence: 4,5,6,6,5,4,3,2,1,1,2,3
Phase lengths: 30,30,31,30,30,31,30,30,31,30,30,31

## Failure boundary

Missing required evidence or boundary geometry fails explicitly. Calendar Core does not silently substitute midnight, noon, a neighboring latitude, a different ephemeris, or an inherited reference point.

## Client boundary

Clients may project a published law. They may not invent the law. A native client may calculate local astronomy for offline display when it uses the versioned protocol and proves conformance against shared vectors. It may not independently select Reconciliation years, a Spring Gate rule, reference authority, evidence authority, or Jubilee epoch.

## Privacy and fixtures

The exact Ground Zero street address and coordinates are not committed. Public conformance vectors use a non-identifying test point and are marked conformance-only. A successful test fixture does not acquire civic jurisdiction.
