# StillPoint Temporal v3.3 — Common Calendar Epoch + Reconciliation Lock

Status: **CANDIDATE — not canonical until Robert Emmanuel LaDay ratifies it.**

This successor does not rewrite or erase the locked v3.2 Reference Rule. v3.2 remains part of the version history. v3.3 corrects two later-identified ontology problems:

1. a completed 364-day ordinary year must not be renamed a 371-day year merely because seven transition days are required before the next opening; and
2. the March equinox need not be the **year-opening instant**. A fixed civic calendar can begin at its own enacted Year/Month/Day 1 while a separately named **Spring Gate inside the year** carries the solar comparison.

That second distinction allows the Common Calendar to preserve familiar fixed dates such as December 25 while still answering the actual Sun.

## Ground Zero

Robert Emmanuel LaDay has designated one private Loveland, Colorado address as **Ground Zero** for the StillPoint pilot.

The exact street address is intentionally **not committed to this public repository**. Public source uses the symbolic reference `GROUND_ZERO`. Deployment supplies the exact geodetic latitude/longitude and a high-entropy custody nonce through an uncommitted configuration file or equivalent private runtime configuration. The public publication contains only a nonce-protected custody commitment unless coordinates are explicitly enacted for publication.

Ground Zero is the local pilot origin for common-clock, horizon, and calendar validation. It does **not** automatically become the permanent national reference point.

## Governing distinction

The ordinary annual vessel is always:

```
B = 364 dusk-boundaries = 52 complete weeks
```

After Day 364, annual jurisdiction is complete. Re-entry into the next ordinary year is either immediate or delayed by one complete Reconciliation interval:

```
R_n ∈ {0, 7}
K_(n+1) = K_n + 364 + R_n
```

Because both 364 and 7 are multiples of seven, weekday identity remains intact.

The Sun does **not** lengthen the finished year. It governs whether re-entry into the next year is immediate or waits one complete week.

## Fixed-date civic grid + solar Spring Gate

The mature annual grid may use the existing StillPoint 30/30/31 × 4 structure:

```
30 + 30 + 31
30 + 30 + 31
30 + 30 + 31
30 + 30 + 31
= 364
```

A fixed annual date keeps the same weekday forever once Day 001's weekday is enacted.

Seasonal correction is not performed by forcing Year Day 001 to sit at the March equinox. Instead, v3.3 names a fixed **Spring Gate** inside each candidate year. The current candidate uses Common Month 3 Day 20:

```
SPRING_GATE_ORDINAL = 80
```

For each transition, compute the two lawful next-year openings:

```
K_immediate = K_n + 364
K_delayed   = K_n + 371
```

Then project each candidate forward to the fixed Spring Gate inside that next year:

```
G_immediate = K_immediate + 79
G_delayed   = K_delayed + 79
```

Compare the apparent-sunset timestamp of those two Spring Gates against the next astronomical March equinox. Choose the candidate with the smaller absolute timing error; exact tie selects immediate re-entry.

This keeps the **date grid fixed** and lets the **Sun correct the seasonal placement of that grid**.

## Candidate civic reference framework

- **Annual solar event A:** astronomical March equinox supplied by a recognized ephemeris.
- **Reference point P:** `GROUND_ZERO` for the pilot; any national point requires separate enactment.
- **Dusk protocol D:** standardized apparent sunset, Sun center approximately -0.8333°.
- **Seasonal target G:** Common Month 3 Day 20 / ordinal 80.
- **Snap operator O:** `NearestLegalSpringGate`.
- **Weekday epoch:** explicit; never inferred silently.
- **Jubilee epoch:** separate jurisdiction.

## Publication contract

A published calendar is an evidence object, not permanent truth. Each publication records:

- version;
- first enacted opening;
- reference identity;
- nonce-protected coordinate custody digest;
- dusk protocol;
- seasonal target;
- ephemeris source and digest;
- snap operator;
- generated year rows;
- canonical publication SHA-256.

Each year row contains exactly 364 ordinary annual days plus `reconciliationDaysAfterCompletion` equal only to 0 or 7.

The Apple Watch loader must fail closed outside the published table instead of extrapolating permanent authority.

## Weekly protected-time geometry

The weekly horizon-break rule is separately ratified in `WEEKLY_PROTECTED_TIME.md`:

- Sabbath = Friday apparent sunset → Saturday apparent sunset;
- Lord's Day = Saturday apparent sunset → Sunday apparent sunset;
- StillPoint = Friday apparent sunset → Sunday apparent sunrise.

This weekly rule does not ratify annual inputs.

## Ratification gate

The unresolved constitutional inputs remain isolated in `RATIFICATION_RECORD.md`. A pilot calibration may be implemented without falsely claiming national enactment.

## Files

- `RATIFICATION_RECORD.md`
- `WEEKLY_PROTECTED_TIME.md`
- `reference.example.json`
- `equinoxes.example.json`
- `published_calendar.schema.json`
- `../../tools/generate_common_calendar_v33.py`

No exact Ground Zero street address or coordinate is committed by this candidate.

## Privacy lock

A bare SHA-256 hash of latitude/longitude is **not** treated as privacy protection. The coordinate commitment is salted with private high-entropy custody material that is never written into the publication.
