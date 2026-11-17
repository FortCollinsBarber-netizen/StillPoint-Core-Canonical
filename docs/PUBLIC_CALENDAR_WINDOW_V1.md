# Public Calendar Window v1 — real read-only capability

**Repository:** FortCollinsBarber-netizen/StillPoint-Core-Canonical.
**Scope:** bounded published-day batch read; does not add calendar law,
expose a private system or authorize a civil or external action.

## Why this capability exists

Existing consumers could request only a single published day at a time.
`calendar_window_payload` returns a **bounded ordered sequence** with
each day's existing `stillpoint.calendar-day.v2` coordinates,
sacred-date mapping, observances, protected-time labels, Jubilee calculations
and publication provenance. Calendar Core retains the law; this merely
composes its established read-only API.

```sh
python -m stillpoint.cli calendar-window 2027 --start-ordinal 83 --days 3
python -m stillpoint.cli calendar-window 2075 --start-ordinal 358 --days 7
```

API:

```python
from stillpoint.calendar_core.runtime_surface import calendar_window_payload
payload = calendar_window_payload(2027, 83, days=3)
assert payload["schema"] == "stillpoint.calendar-window.v1"
assert len(payload["days"]) == 3
```

The response carries `schema`, `authority`, `calendar_day_schema`,
`request`, `bounds`, `map`, `publication`,
`sacred_year_profile`, `long_cycle_policy`,
`civil_or_legal_execution_authorized: false`, and `days`.

## Hard limits

- Only **1–31 days** per request; the default is seven.
- All days must belong to the **same published Common year**; no
  automatic year-boundary carry or fabricated intercalary day.
- The source publication remains **2026–2075**. Year 2076 is
  mathematical Jubilee projection only, not a published calendar.
- The selected March 25 source-year anchor and 2027 overlap-49 Jubilee
  remain **author-selected working rules, not civil enactment**.
- The CLI performs the read before constructing `CompanyRuntime`,
  contacting a model/provider, or opening company state.
- All entries come from the established `calendar_day_payload` function.
  The batch surface is not a second calendar engine or a license to mutate
  the grid. It cannot claim to qualify private RobertOS/StillPointOS code.

## Run public tests

```sh
python -m unittest discover -s tests/calendar_core -p 'test_calendar_window.py' -v
python -m unittest discover -s tests -q
```

When CI passes, this is a distributable public Core operator capability
in the existing repository and current package. Its future authority remains
revisable through the documented authorization and qualification process.
