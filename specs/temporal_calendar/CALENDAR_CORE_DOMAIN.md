# StillPoint Calendar Core — Executable Domain Contract

stillpoint.calendar_core is the platform-neutral calendar and clock engine.

It is deliberately separate from stillpoint.temporal. The latter already owns
StillPoint temporal-authority and continuing-evidence semantics. The calendar
engine describes time; the authority engine governs what descriptions may
authorize. Neither namespace silently inherits the other's powers.

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

## Weekly rule

Sabbath:
Friday apparent sunset through Saturday apparent sunset.

Lord's Day:
Saturday apparent sunset through Sunday apparent sunset.

StillPoint:
Friday apparent sunset through Sunday apparent sunrise.

The intervals are half-open at their closing boundary.

## Annual custody

Recovered v3.2 remains callable under its own version.

The current v3.3 successor candidate uses:
364 ordinary days, then 0 or 7 interannual Reconciliation days, then the next
ordinary year. Its current candidate Spring Gate is Common Month 3 Day 20,
ordinal 80.

## Six paired gates

The recovered gate sequence is:
4,5,6,6,5,4,3,2,1,1,2,3

The twelve phase lengths are:
30,30,31,30,30,31,30,30,31,30,30,31

Any old twelve-unrelated-gate representation is lineage, not executable law.

## Authority boundary

Calendar Core calculates and returns state. It does not send messages, publish,
spend, contract, delete, silence third-party applications, or otherwise perform
external actions. Those actions remain downstream of StillPoint authority
gates.

## Golden pilot vector

Observation Zero is a calibration instant, not Day 1.

With:
- opening civil date 2026-01-01;
- Friday as Day-001 weekday;
- America/Denver as legal civil zone;
- permanent Common Clock offset UTC-07;

the instant 2026-09-18T19:28:57Z maps to:
- Common Year 2026;
- Day 260;
- Month 9 Day 18;
- Quarter 3;
- Week 38;
- Friday;
- legal civil offset UTC-06;
- Common standard offset UTC-07.
