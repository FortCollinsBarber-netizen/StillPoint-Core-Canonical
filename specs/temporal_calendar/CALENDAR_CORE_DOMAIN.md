# StillPoint Calendar Core — Platform-Neutral Domain

`stillpoint.calendar_core` is the pure calendar geometry and address engine.

It is deliberately separate from:

- `stillpoint.calendar_publication`, which binds explicit authority inputs to
  evidence and compiles finite civic coordinates;
- `stillpoint.calendar_witness`, which owns Jubilee and later lunar/season/
  feast witness layers;
- `stillpoint.temporal`, which owns continuing-evidence, warrant, expiration,
  correction, and external-action authority.

## Engineering invariant

The week governs sequence. The ordinary calendar governs address. The Sun
governs seasonal correction. The Moon and seasons provide evidence. Publication
gives finite civic coordinates. Jubilee governs a larger release count. None of
them owns the others.

## Core namespaces

### Continuous

`K = 0,1,2,...` over adopted dusk boundaries. Sequence does not gap.

### Ordinary annual

`Y_n-001 ... Y_n-364`.

Month, quarter, phase, gate, and ordinary day-of-year exist only here.

### Reconciliation

`Y_n/Y_(n+1)-R1 ... R7`.

Reconciliation may contain exactly zero or seven dusk boundaries. It is not
Days 365–371 and receives no ordinary month, quarter, phase, gate, or
day-of-year.

A projection after the supplied annual/reconciliation range returns
`OUTSIDE_RANGE`: continuous sequence may remain knowable while annual address
authority has expired.

## Stable geometry

- 364 ordinary days = 52 complete weeks = 4 x 91 days.
- month/phase lengths: 30,30,31 repeated four times.
- gate sequence: 4,5,6,6,5,4,3,2,1,1,2,3.
- apparent horizon baseline: Sun-center altitude about -0.8333 degrees.
- no silent boundary fallback.

## Weekly protected-time geometry

- Sabbath: Friday apparent sunset -> Saturday apparent sunset.
- Lord's Day: Saturday apparent sunset -> Sunday apparent sunset.
- StillPoint: Friday apparent sunset -> Sunday apparent sunrise.

Intervals are half-open at their closing boundary.

## Artifact boundary

Stable law exports as `calendar_core_spec.json`.

Public/pilot enactment is not part of that artifact. A finite
`calendar_publication.json` is compiled by `stillpoint.calendar_publication`
from explicit authority inputs plus evidence custody.

Cross-platform conformance data exports separately as
`calendar_projection_vectors.json`. Observation Zero and the public Loveland
test point are proof fixtures, not law and not Ground Zero.

The former aggregate Calendar Core contract remains compatibility-only until
stacked Apple work is migrated.
