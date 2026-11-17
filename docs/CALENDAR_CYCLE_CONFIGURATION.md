# Calendar cycle configuration and observance scope

Calendar runtime responses now identify the existing Jubilee calculation's
epoch and rollover rule, preserve observance scope, and provide an arithmetic
comparison of long cycles. These additions do not select a new operative
rollover or sacred-year anchor.

## Existing behavior and explicit configuration

Calling `calendar_day_payload(year, ordinal)` still uses the publication's
first year as the historical default Jubilee epoch. Its response now identifies
`legacy-publication-first-year-default`, `standalone-50`, and
`rollover-reconciliation-unresolved`. This is compatibility behavior, not an
assertion that an unresolved decision has been settled.

The epoch may be supplied independently:

```python
from stillpoint.calendar_core import JubileeConfiguration
from stillpoint.calendar_core.runtime_surface import calendar_day_payload

value = calendar_day_payload(
    2075, 1,
    jubilee_configuration=JubileeConfiguration(epoch_common_year=2027),
)
assert value["jubilee"]["year"] == 49
```

The Common date, external projection, publication identity, and annual grid
are unchanged. Passing `JubileeConfiguration(epoch_common_year=None)` explicitly
requests no designation; consumers must use `designation_status` rather than
interpreting an absent designation as a settled negative finding. An explicit
calculation input is not evidence of a civic or religious enactment. Unsupported
operational rollover identifiers are rejected rather than silently mapped to
the existing counter.

The original finite publication still rejects Common 2076. An arithmetic model
can examine a later year without extending publication coverage.

## Compare cycles without selecting a release rule

```python
from stillpoint.calendar_core import compare_long_cycles

comparison = compare_long_cycles(common_year=2076, epoch_common_year=2027)
```

The comparison separately reports continuous seven-year position, six-year
priestly-course phase, consecutive 49-year blocks, and the existing standalone
50-year counter. The phase origin is the start of epoch Year 1. At 49 elapsed
years, ordinal Year 50 and the next 49-year block begin together, while the
weekly-course phase has advanced four positions. The comparison leaves the
proclamation rule unresolved.

Under the explicit assumptions of 52 weeks per year and 24 uninterrupted
weekly courses, the joint six-/seven-/49-year recurrence is 294 years. Adding
an independent 50-year cycle changes the joint recurrence to 7,350 years.
Neither calculation grants release authority, predicts a prophetic event,
corrects seasonal drift, or changes a civil date. The response states
`scope: arithmetic-comparison-only`, `grid_authority: false`, and
`release_authority: false`. A missing epoch yields no model positions.

## Preserve observance provenance

Runtime observance entries retain `id` and `name` and now include `jurisdiction`,
`rule`, `source_refs`, `note`, the recorded Common coordinate and projection
status. A religious or sacred-marker entry's fixed Common placement is labeled
`legacy-placement-unreconciled-sacred-anchor`. The software does not relabel
that recorded coordinate as a verified scriptural coordinate.

The legacy Jubilee-release boolean is likewise accompanied by an unresolved
sacred-anchor projection status. It is not proof of an authorized sacred-year
mapping, discharge of an obligation, or permission to act. A future migration
must reconcile those legacy placements with an explicit selected profile;
this change does not pretend that migration has occurred.

The fixed 364-day grid, publication bytes, existing weekday geometry, and
separation of action warrants from calendar evidence are preserved. There is
no new cloud dependency or competing calendar engine.
