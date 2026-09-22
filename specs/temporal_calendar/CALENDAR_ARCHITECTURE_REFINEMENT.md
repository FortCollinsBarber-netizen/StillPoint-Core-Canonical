# Calendar Architecture Refinement

Status: **ENGINEERING TARGET — branch refinement of PR #15 lineage**

This document freezes the module boundary before Core CI and Apple Watch CI are
rewritten around it.

## Governing invariant

> The week governs sequence. The ordinary calendar governs address. The Sun
> governs seasonal correction. The Moon and seasons provide evidence.
> Publication gives finite civic coordinates. Jubilee governs a larger release
> count. None of them owns the others.

## Four frozen engineering invariants

1. **Continuous sequence is sovereign only over sequence.** `K` never gaps.
   Weekday continuity survives ordinary years and Reconciliation.
2. **The ordinary year is always 364 ordinary days.** Reconciliation is never
   Days 365–371 and inherits no month, quarter, phase, gate, or ordinary
   day-of-year.
3. **Evidence does not enact itself.** Sun, Moon, equinox, solstice, and other
   observations may supply evidence to a finite publication decision; they do
   not grant themselves authority.
4. **Clients project law; they do not make it.** Native clients may perform
   bounded local astronomy and offline projection. Publication decisions,
   authority status, reference identity, and evidence custody come from
   versioned StillPoint artifacts.

## Dependency direction

```
reality/evidence
      |
      v
geometry + Calendar Core law
      |
      v
finite calendar publication
      |
      +----> witness/meta layers
      |
      v
client projection
```

`stillpoint.temporal` remains orthogonal. It governs temporal authority,
warrants, expiration, correction, and action jurisdiction. Calendar code does
not inherit those powers.

## Package ownership

### stillpoint.calendar_core

Owns:

- standardized apparent rise/set geometry;
- continuous `K` sequence;
- seven-day continuity;
- ordinary 364-day address grid;
- 30/30/31 x 4 month geometry;
- quarters, weeks, weekdays;
- six paired Enoch gates / twelve phases;
- explicit ORDINARY / RECONCILIATION / OUTSIDE_RANGE projection states;
- Sabbath, Lord's Day, and StillPoint weekly geometry.

Does not own:

- national/civic reference-point enactment;
- ephemeris authority;
- publication authority;
- Jubilee epochs;
- lunar or season witness custody;
- external actions.

### stillpoint.calendar_publication

Owns finite compilation from explicit authority inputs plus evidence:

- versioned reference-rule selection;
- Spring Gate candidate evaluation;
- `R_n in {0,7}` publication decisions;
- finite effective range;
- evidence digest;
- reference geometry digest;
- publication digest.

Evidence cannot compile a publication without an explicit authority status and
authority identifier.

### stillpoint.calendar_witness

Owns larger-cycle or observational annotations such as Jubilee, lunar witness,
season witness, and feast/observance metadata. These layers may consume Common
Calendar coordinates but cannot redefine Calendar Core.

## Artifact split

### calendar_core_spec.json

Stable machine-readable law. It contains no pilot coordinates, Observation Zero
epoch, ephemeris selection, Jubilee epoch, or publication authority.

### calendar_publication.json

Finite output of the publication compiler. It carries explicit authority status,
rule version, reference identity/digest, evidence identity/digest, epoch,
effective range, year rows, and publication digest.

No canonical publication is checked in merely because compilation works.
Ratification remains separate.

### calendar_projection_vectors.json

Cross-platform proof data. Conformance locations and calibration instants live
here, not in the stable law artifact. Negative vectors must prove that
Reconciliation receives no ordinary address and that projections fail closed
outside the finite publication range.

## Compatibility

The old `calendar_core_contract.json` aggregate is transitional only.
`stillpoint.calendar_core.contract` remains as a compatibility exporter so
stacked Apple work can be restacked intentionally. New consumers must use the
three-artifact architecture.

The old `stillpoint.calendar_core.reference_rule` and
`stillpoint.calendar_core.jubilee` paths remain compatibility shims. New code
uses `stillpoint.calendar_publication` and `stillpoint.calendar_witness`.

## Pilot custody

Pilot material belongs under `calendar/pilots/`. A conformance fixture may
prove arithmetic without becoming Ground Zero. A pilot may prove usability
without ratifying national law. Neither belongs in the stable Core spec.

## CI sequence after this refinement

1. prove Calendar Core domain tests explicitly;
2. prove finite publication compiler from frozen evidence fixtures;
3. prove deterministic generated artifacts;
4. prove installed-wheel artifact generation;
5. restack Apple to consume the split artifacts;
6. run cross-language positive and fail-closed vectors;
7. build Watch app and WidgetKit;
8. only then restack Jubilee/lunar/season work from PR #14.
