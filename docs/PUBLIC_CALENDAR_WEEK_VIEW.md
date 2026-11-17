# Public Common Calendar week view

This new capability reads **one complete seven-day Common Calendar week** from
the existing enacted 364-day calendar. It reuses the public Core day projection.
No new calendar engine, private repository, account, database, or service is
required.

## Usage

Install Core (`python -m pip install .`) or run from this source checkout:

```sh
python -m stillpoint.cli calendar-week 2026 --week 1
python -m stillpoint.cli calendar-week 2075 --week 52
```

The command prints JSON with `stillpoint.calendar-week.v1`, year and week,
the seven Common addresses, named dates and weekdays, source-date overlay,
observance names and jurisdictions, Sabbaths, and published-range metadata.
This is a **read-only projection**; it does not open the company database or
require credentials, third-party APIs, any network fetch, or GitHub Actions at
runtime.

Week 1 always comprises ordinals 001–007; week 52 comprises 358–364. A
week is based on the internal 52-week Common year, not ISO/Gregorian weeks.
The external Gregorian `civil_window` for each day is retained only as an
interoperability coordinate, **not calendar law**.

Only published years **2026–2075** are supported. A request for 2076 or an
invalid week fails closed. Mathematical 2076 Jubilee interpretation never
creates a 2076 published day or a legal release. The existing sacred-year
profile, its March 25 anchor, 2027 epoch, and 49-year rollover remain
unchanged. Nothing in a read-only week payload confers an external civic
or religious mandate.

## Python use

```python
from stillpoint.calendar_core.week_view import calendar_week_payload

week = calendar_week_payload(2026, 1)
assert week["day_count"] == 7
assert week["first_address"] == "Y_2026-001"
```

The `days` list deliberately exposes a bounded subset of each already
published `calendar_day_payload`: Common date, external civil window,
sacred-source reference date, observance summary, and Sabbath-date marker.
For the full provenance and boundary annotations, use `calendar-day YEAR
--ordinal N` instead. A Sabbath **date marker** is not a location-specific
sunset or civil twilight instant; use the existing `clock-at` or
`clock-window` interfaces with explicit location and zone for those.

## Tests

```sh
python -m unittest discover -s tests/calendar_core -p 'test_public_week_view.py' -q
```

The existing public Core CI also discovers and executes these tests. Passing
them does not qualify private RobertOS or StillPointOS commits.
