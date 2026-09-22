# Weekly Protected-Time Geometry — Horizon-Break Rule

**Status:** RATIFIED WEEKLY RULE  
**Ratifying authority:** Robert Emmanuel LaDay  
**Scope:** weekly StillPoint, Sabbath, and Lord's Day boundaries  
**Effect on Temporal v3.3:** this weekly geometry is settled independently of the three still-unratified annual-calendar inputs.

## 1. The Horizon-Break Boundary

For calendrical computation, "the Sun breaks the horizon" means the conventional **apparent sunrise / apparent sunset** boundary already compatible with the StillPoint dusk protocol:

- geometric zenith distance of the Sun's center: **90° 50′ = 90.8333°**;
- equivalent center altitude: approximately **-0.8333°**;
- assumed level, unobstructed horizon and average atmospheric refraction;
- **sunrise:** the upper limb of the Sun first reaches / appears at the eastern horizon;
- **sunset:** the upper limb of the Sun last reaches / disappears at the western horizon.

This is the legal computational boundary. Terrain, buildings, weather, observer elevation, and unusual refraction may change what a particular eye sees. Those remain local witness conditions; they do not silently move the calendar's standardized boundary.

The same geometric standard governs both sunrise and sunset so the weekly architecture does not use one definition to open an interval and another to close it.

## 2. Four Weekly Boundaries

For a locality `p` and a civil week `w`, define:

```
F↓ = Friday apparent sunset
S↓ = Saturday apparent sunset
U↑ = Sunday apparent sunrise
U↓ = Sunday apparent sunset
```

The arrows name the solar direction across the apparent horizon:

- `↓` = setting / disappearing below the western horizon;
- `↑` = rising / appearing above the eastern horizon.

All intervals are half-open: **[start, end)**. The opening boundary belongs to the interval that begins there; the closing boundary belongs to the next jurisdiction.

## 3. Sabbath

```
SABBATH_w = [ F↓ , S↓ )
```

Sabbath begins **exactly at Friday apparent sunset** and ends **exactly at Saturday apparent sunset**.

At Friday sunset:
- Sabbath begins;
- StillPoint begins.

At Saturday sunset:
- Sabbath is complete;
- Lord's Day begins.

Saturday sunset itself belongs to Lord's Day, not to the completed Sabbath.

## 4. Lord's Day

```
LORDS_DAY_w = [ S↓ , U↓ )
```

Lord's Day begins **exactly at Saturday apparent sunset** and ends **exactly at Sunday apparent sunset**.

Sunday sunrise does **not** end Lord's Day. It ends StillPoint while Lord's Day continues through the daylight portion of Sunday until Sunday sunset.

## 5. StillPoint

```
STILLPOINT_w = [ F↓ , U↑ )
```

StillPoint begins **exactly at Friday apparent sunset** and ends **exactly at Sunday apparent sunrise**, the moment the Sun's upper limb breaks the eastern horizon under the standardized apparent-horizon rule.

Therefore:

```
STILLPOINT_w
  = SABBATH_w
    ∪ [ S↓ , U↑ )
```

StillPoint contains:
1. the whole Sabbath; and
2. the nighttime opening portion of Lord's Day, from Saturday sunset until Sunday sunrise.

It does **not** contain the daylight remainder of Lord's Day after Sunday sunrise.

## 6. Weekly State Map

```
Friday daytime
    |
    | F↓  FRIDAY SUNSET
    v
+-----------------------------+
| SABBATH                     |
| STILLPOINT                  |
+-----------------------------+
    |
    | S↓  SATURDAY SUNSET
    v
+-----------------------------+
| LORD'S DAY                  |
| STILLPOINT                  |
+-----------------------------+
    |
    | U↑  SUNDAY SUNRISE
    v
+-----------------------------+
| LORD'S DAY                  |
| StillPoint released         |
+-----------------------------+
    |
    | U↓  SUNDAY SUNSET
    v
ordinary weekly time
```

The sequence is therefore:

```
F↓        S↓        U↑        U↓
|---------|---------|---------|
SABBATH
|-------------------|
STILLPOINT
          |-------------------|
          LORD'S DAY
```

The drawn lengths are schematic. Actual clock durations vary seasonally because the calendar follows solar boundaries rather than fixed wall-clock hours.

## 7. Jurisdiction Rules

These three intervals must remain distinct even when they overlap.

- **Sabbath** answers which dusk-to-dusk day is the seventh-day cessation.
- **Lord's Day** answers which dusk-to-dusk day runs from Saturday sunset through Sunday sunset.
- **StillPoint** answers the larger protected weekly threshold from Friday sunset through Sunday sunrise.

No interval inherits the other's full meaning merely because they overlap.

In particular:

- Sabbath is not renamed StillPoint.
- Lord's Day is not shortened to sunrise.
- StillPoint is not extended to Sunday sunset.
- Sunday sunrise is a **release boundary for StillPoint**, not the end of Lord's Day.

## 8. Calendar / Device Contract

Every client implementing the Common Calendar must be able to expose these four computed instants for the user's authorized locality:

```
fridaySunset
saturdaySunset
sundaySunrise
sundaySunset
```

At minimum, a device must derive and expose these booleans:

```
isSabbath
isLordsDay
isStillPoint
```

And the state transitions must be exact:

```
now < F↓                         => none
F↓ <= now < S↓                   => Sabbath + StillPoint
S↓ <= now < U↑                   => Lord's Day + StillPoint
U↑ <= now < U↓                   => Lord's Day
U↓ <= now                        => none
```

For the Apple Watch, the active state should be visible without collapsing the jurisdictions. During the overlap after Saturday sunset, the display may truthfully show both **LORD'S DAY** and **STILLPOINT**.

## 9. Relationship to Annual Calendar

This weekly rule does not ratify:

- the first Common Calendar year opening;
- the national Reference Rule point P;
- the March-equinox evidence source;
- the Jubilee epoch.

Those remain separate decisions in `RATIFICATION_RECORD.md`.

The annual system counts sunset boundaries. This weekly protected-time layer additionally uses one sunrise boundary — Sunday sunrise — solely to close the StillPoint protected interval. That sunrise does not alter the dusk-to-dusk day count or the seven-day week.

## 10. Canonical Sentence

**Sabbath is Friday sunset to Saturday sunset. Lord's Day is Saturday sunset to Sunday sunset. StillPoint is Friday sunset to Sunday sunrise. The same apparent horizon defines every opening and release.**
