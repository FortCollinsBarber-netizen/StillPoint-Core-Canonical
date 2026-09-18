# StillPoint Jubilee / Feast / Lunar Cycle v1

**Status: CANDIDATE — bounded separately from Temporal v3.3 annual ratification**

This layer builds the fifty-year release cycle, fixed-date feast grid, lunar observation layer, and permanent-standard Common Clock without changing the already-set weekly horizon rule or silently resolving the three still-open annual v3.3 inputs.

## 1. Jurisdictions

StillPoint now keeps six temporal jurisdictions distinct:

1. **Horizon day** — local apparent sunset to local apparent sunset.
2. **Week** — seven successive dusk boundaries.
3. **Ordinary year** — 364 ordinary annual days = 52 weeks.
4. **Reconciliation** — optional 0-or-7-day interannual interval; not part of either ordinary year.
5. **Jubilee count** — seven seven-year cycles (49 years) followed by the fiftieth-year Jubilee threshold.
6. **Lunar witness** — observed/calculated lunar phase events. The Moon does not secretly redefine month lengths.

The Moon may mark reality without owning the date grid. This is required if fixed weekday identity, a 364-day year, and actual lunar phases are all to remain true at once.

## 2. Fixed annual grid

The ordinary year keeps the mature StillPoint structure already present in the manuscript:

```
364 = 52 × 7 = 4 × 91
91 = 13 × 7

month lengths:
30, 30, 31,
30, 30, 31,
30, 30, 31,
30, 30, 31
```

The familiar month names January through December may be used as civic labels for those twelve annual phases.

Every annual date has a permanent day-of-week once the weekday epoch is enacted because every displacement from one year opening to the next is a whole number of weeks:

```
364 + R_n ≡ 0 (mod 7),  R_n ∈ {0,7}
```

No isolated leap day exists.

## 3. 2026 weekday-freeze candidate

Robert's stated rule is that a date should retain the weekday it is assigned at adoption. Two concrete 2026 anchors are internally consistent with the 30/30/31 grid:

- December 10, 2026 is Thursday.
- December 25, 2026 is Friday.

Under the 30/30/31 × 4 grid, both constraints imply:

```
COMMON YEAR DAY 001 = FRIDAY
```

This branch therefore records **Friday Day-001 as the candidate weekday epoch**. It does not by itself choose the astronomical timestamp of the first annual opening. That remains an annual v3.3 ratification decision.

With this epoch, Common December 10 is Thursday every ordinary year and Common December 25 / Christmas is Friday every ordinary year. Reconciliation does not change either weekday because it is a whole week outside the completed year.

## 4. Jubilee cycle

The fifty-year structure is represented as:

```
Years 1–7    cycle 1
Years 8–14   cycle 2
Years 15–21  cycle 3
Years 22–28  cycle 4
Years 29–35  cycle 5
Years 36–42  cycle 6
Years 43–49  cycle 7
Year 50      Jubilee
```

Years 7, 14, 21, 28, 35, 42, and 49 are sabbatical/release thresholds.

Year 50 is the Jubilee year. The Jubilee proclamation/release gate is attached to the fixed annual Day of Atonement date (Month 7, Day 10), following the Levitical sequence of counting seven sabbaths of years, reaching forty-nine, then proclaiming liberty at the fiftieth-year threshold.

The implementation does not pretend that weekly Sabbath, land rest, Deuteronomic debt remission, service release, and Levitical Jubilee are one undifferentiated legal rule. They share temporal architecture while retaining separate legal/theological content.

## 5. Observation Zero — 2026-09-18

The present moment is used as **Observation Zero**, not silently as Common Year 1 Day 1.

At the recorded local check on 2026-09-18 in Loveland, Colorado:

- the civil/legal zone was MDT (UTC−06);
- the permanent-standard Common Clock counterpart was MST (UTC−07);
- the Moon was waxing crescent and approaching first quarter;
- USNO places first quarter at 2026-09-18 20:44 UTC = 14:44 MDT;
- USNO places the September equinox at 2026-09-23 00:05 UTC = 2026-09-22 18:05 MDT.

Observation Zero tells us where the sky actually is when the new architecture is being built. It does not force a mid-year annual epoch. The first Jubilee year should begin with the first **ratified Common Calendar opening** after Observation Zero unless Robert explicitly enacts a different Jubilee epoch.

See `OBSERVATION_ZERO_2026-09-18.md`.

## 6. Lunar rule

A synodic month is not an integer divisor of 364 days. Therefore an actual new moon cannot remain on one fixed Common Calendar date every year without sacrificing either the observed Moon or the fixed solar-week calendar.

The rule is therefore:

- fixed feasts belong to the Common Calendar;
- actual new/quarter/full/last-quarter events belong to the lunar evidence layer;
- a feast may record the Moon phase present that year without moving merely because the Moon moved;
- any explicitly lunar observance must state that it is phase-governed and therefore may move across fixed civic dates;
- the lunar evidence source must be versioned and digestible just like equinox evidence.

No mean lunar table receives permanent authority over observed/calculated phase evidence.

## 7. Permanent-standard Common Clock

For Ground Zero / Colorado pilot use:

- **Legal civil clock:** the device/system civil time, including DST when civil law applies it.
- **Common Clock:** permanent standard local time, MST / UTC−07 year-round.
- **Solar boundary:** an astronomical instant independent of either label.

The two clocks are translations of one instant. Neither changes the sunrise/sunset event.

This makes "no daylight savings" true inside the Common Clock without falsely claiming that current Colorado civil law has already abolished DST.

## 8. Civic ↔ Common bidirectional mapping

Every public instant should be representable as both:

```
LEGAL CIVIC STAMP
Gregorian date + legal local clock + zone

COMMON STAMP
Common year/month/day + fixed weekday + permanent-standard clock
+ Sabbath/Lord's Day/StillPoint state
+ season position
+ lunar phase evidence
+ Jubilee cycle position
```

The conversion is bidirectional through the same UTC instant and the published Common Calendar table. No translation layer owns the underlying event.

## 9. Holiday registry

Fixed annual holidays are data, not hard-coded conditionals. A registry entry may be:

- `fixed_date` — e.g. Christmas = Month 12 Day 25;
- `weekday_ordinal` — e.g. fourth Thursday of a month;
- `seasonal_gate` — a named gate tied to the annual structure;
- `lunar_event` — explicitly phase-governed and allowed to move.

Under a fixed weekday grid, a weekday-ordinal observance also resolves to the same annual date every year.

## 10. Still unresolved

This layer does **not** resolve:

- first enacted Common Calendar opening;
- national/civic Reference Rule point;
- ratified equinox evidence source;
- exact first Jubilee Year 1 opening if different from the first Common Calendar opening.

Those remain explicit ratification decisions. The code must fail closed until they exist.


## 11. Pilot epoch and real Observation-Zero coordinate

The user has now authorized an engineering calibration that starts from the real present without pretending the present is Day 1.

For the **pilot**:

```
COMMON YEAR LABEL          = 2026
DAY 001 OPENS              = apparent sunset on civil 2026-01-01 at Ground Zero
DAY 001 WEEKDAY            = Friday
OBSERVATION ZERO           = 2026-09-18 13:28:57 MDT
ACTIVE PRECEDING BOUNDARY  = apparent sunset on civil 2026-09-17
COMMON POSITION            = Year 2026 · Day 260 · Month 9 Day 18
                              Quarter 3 · Quarter Day 78
                              Week 38 · Day-in-week 1 · Friday
```

This makes Observation Zero a real coordinate inside an already-running pilot year.

The same pilot also establishes:

```
JUBILEE PILOT CYCLE = 1
JUBILEE PILOT YEAR  = 1
COMMON YEAR         = 2026
```

This is a modern pilot epoch, not a claim about an ancient Jubilee chronology.

## 12. Why the Spring Gate moved inside the year

The fixed-date requirement exposed a necessary correction to the annual engineering.

If Christmas is to remain Common December 25 and annual dates are to keep permanent weekday identity, the Common year should not be forced to open at the March equinox. Instead the Common year keeps its own fixed civic grid and the Sun audits a **Spring Gate inside it**.

The current candidate uses:

```
Common March 20 = ordinal day 80 = Spring Gate
```

Reconciliation selects between the two lawful next-year openings by asking which candidate places **next year's Common March 20 sunset** closer to the next astronomical March equinox.

That keeps all four truths:

- fixed dates stay fixed;
- weekdays stay fixed;
- the 364-day year stays complete;
- the Sun can still correct seasonal drift.

