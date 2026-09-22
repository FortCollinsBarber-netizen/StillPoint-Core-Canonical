# Ground Zero 2026 Pilot Namespace

This directory is reserved for pilot-only calendar material.

It is deliberately separate from `stillpoint/contracts/` so Observation Zero,
private Ground Zero geometry, pilot epochs, and temporary witness data cannot
silently become Calendar Core law.

## Custody rules

- Calendar Core does not import anything from this directory.
- Exact private Ground Zero coordinates are not committed.
- A pilot publication must identify itself as `authority.status = PILOT`.
- Pilot evidence may generate finite coordinates only through the publication
  compiler.
- A successful pilot does not ratify a national reference point, ephemeris
  source, first enacted opening, or Jubilee epoch.
- When PR #14 is restacked, its 2026 calibration, lunar witness, season witness,
  and Jubilee pilot material belong here (or in a sibling pilot evidence
  directory), not in the stable Calendar Core spec.

There is intentionally no canonical `calendar_publication.json` checked in
here yet. Publication requires explicit authority inputs and evidence custody.
