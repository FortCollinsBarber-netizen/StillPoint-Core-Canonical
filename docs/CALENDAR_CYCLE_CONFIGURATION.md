# Cycle and sacred-year configuration: selected working rules

**Status:** working source-calendar anchor and overlapping rollover selected
by Robert Emmanuel LaDay on November 17, 2026. The selection governs the
StillPoint working implementation, not ancient history, religious communities,
or civil law.

The decision record and evidentiary limits are in `CALENDAR_RULE_RESOLUTION_2026-11-17.md`.

## Author-selected working defaults

- Common long-cycle Year 1 begins January 1, 2027, independently of publication.
- Consecutive 49-year blocks; a fiftieth proclamation overlaps the next Year 1.
- Source months are 30/30/31, with source I/1 at Common March 25, Wednesday.
- Firstfruits is source I/26; Weeks is III/15, inclusive Day 50.
- The source VII/10 appointment projects to Common October 2. A date label
  does not execute a legal release or determine its astronomical instant.

The fixed 364-day civil grid, standard clock and finite publication are
unchanged. No annual solar realignment occurs. Other communities retain their
religious calendars and Firstfruits interpretations.

## Versioned interfaces

The runtime response is `stillpoint.calendar-day.v2`. Population content uses
`stillpoint-calendar-population-v2`; its carrier filename remains
`calendar_population_v1.json` for the existing bundle/build path. The internal
version and checksum identify the contract. The new Watch loader rejects old
or incompatible data rather than applying its old publication-index inference.

```python
from stillpoint.calendar_core import JubileeConfiguration, common_from_sacred
from stillpoint.calendar_core.runtime_surface import calendar_day_payload

day = calendar_day_payload(2075, 1)
assert day["jubilee"]["year"] == 49
assert not day["jubilee"]["is_jubilee_year"]
first = common_from_sacred(2027, 1, 26)
assert (first.month, first.day, first.weekday) == (4, 19, "Sunday")
```

An explicit None epoch requests no designation. Another explicit epoch does
not change the civil map. `rollover_rule="standalone-50"` keeps the former
counter available as a named alternative; unsupported identifiers fail.

The sacred year label runs from Common March 25 through the following March
24. Common long-cycle years still change on January 1. Source and projected
coordinates are stored separately. The first calculated working proclamation in 2076
remains outside the current 2026–2075 publication: arithmetic can examine that
year, but runtime calendar payloads must reject it until a separate extension.

Historical PR #82 behavior is preserved at
`a5fe5fbcb8889e60df7cc1a11c2a7462659063fb`.
