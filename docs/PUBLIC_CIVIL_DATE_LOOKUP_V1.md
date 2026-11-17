# Public civil-date lookup — ordinary date to StillPoint Calendar

**Status:** public-only engineering capability; read-only; no new calendar law or legal/civic enactment.

## What people can do

Given an ordinary Gregorian civil date, the tool returns the matching
**already-published** StillPoint Common Calendar year, ordinal, weekday,
sacred-source projection, observances, Jubilee information and custody metadata.
People no longer need to work out the StillPoint year and ordinal themselves.

Use the **existing public Canonical Core repository**; no new repository, service,
private-system checkout, sign-in, model token, database or paid cloud resource
is needed at runtime.

## Install and use

From a checkout of the public repository:

```sh
python -m pip install .
stillpoint-date 2026-11-17
```

Or run the module directly (also useful in environments without installed
console-script entry points):

```sh
python -m stillpoint.calendar_core.civil_lookup 2026-11-17
```

The command prints JSON using the `stillpoint.civil-date-lookup.v1` schema
with fields `civil_date`, `translation`, and `calendar_day`. The nested
`calendar_day` is the **same v2 payload** returned by the existing public
`calendar-day YEAR --ordinal DAY` interface. Its `common_date`,
`calendar_address`, `civil_window`, `sacred_date`, `protected_time`,
`jubilee`, `observances`, `map` and `publication` fields retain the
existing jurisdiction and provenance boundaries.

For Python consumers:

```python
from stillpoint.calendar_core.civil_lookup import civil_date_lookup_payload

result = civil_date_lookup_payload("2026-11-17")
assert result["calendar_day"]["civil_window"]["opens"] == "2026-11-17"
```

## Calendar rules and limits

- The Gregorian date is a **translation coordinate only**. It does not govern
  or modify the 364-day/52-week Common Calendar.
- A Common year is **not** a Gregorian calendar year. For example, civil
  `2026-12-30` is StillPoint `Y_2026-364`, while civil `2026-12-31`
  is `Y_2027-001`, because the next Common year starts 364 days after
  January 1, 2026.
- The selected March 25 sacred source-year anchor, separate 2027 Jubilee
  epoch, 49-year overlapping rollover, distinct sacred sunset and civil dusk/
  dawn protections, and nine jurisdictional layers are unchanged.
- Only the currently enacted **50-year finite publication**, Common years
  **2026–2075**, is available. A Gregorian date outside its actual external
  projection interval fails closed. In particular this command does **not**
  issue a Common year 2076 merely because mathematical Jubilee calculations
  can describe it.
- Invalid dates, e.g. `2026-02-29`, and non-ISO input fail with a nonzero
  exit code and **no JSON calendar payload**. The CLI creates no company state.
- Lookup performs no location-based solar event calculation. The returned
  civil twilight and sacred sunset descriptions are rules, **not** measured
  local clock times. Use existing explicitly location-bound Clock OS functions
  for actual local instants.

The translation is computed from the validated opening rows in the existing
published calendar, then the preexisting read-only day projection is invoked.
No parallel calendar engine or independent source of Calendar authority exists.

## Testing and availability

```sh
python -m unittest discover -s tests/calendar_core -p 'test_civil_lookup.py' -v
```

The tests verify first/last published days, the 364-day New Year boundary,
Gregorian leap-day alignment, invalid/out-of-publication inputs, and execution
from a clean external working directory without provider keys or state writes.
Normal Core CI additionally builds the existing public distribution and runs
the calendar suites on GitHub's standard public Ubuntu runners.

This is a **downloadable/locally runnable public software feature**, not
a claim that a hosted website, Apple Watch installation, or the preserved
private RobertOS/StillPointOS integration has been deployed or qualified.
