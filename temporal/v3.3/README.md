# StillPoint Temporal v3.3 — Common Calendar Epoch + Reconciliation Lock

Status: **CANDIDATE — not canonical until Robert Emmanuel LaDay ratifies it.**

This successor does not rewrite or erase the locked v3.2 Reference Rule. v3.2 remains part of the version history. v3.3 corrects one later-identified ontology problem: a completed 364-day ordinary year must not be renamed a 371-day year merely because seven transition days are required before the next opening.

## Ground Zero

Robert Emmanuel LaDay has designated one private Loveland, Colorado address as **Ground Zero** for the StillPoint pilot.

The exact street address is intentionally **not committed to this public repository**. Public source uses the symbolic reference `GROUND_ZERO`. Deployment supplies the exact geodetic latitude/longitude and a high-entropy custody nonce through an uncommitted configuration file or equivalent private runtime configuration. The public publication contains only a nonce-protected custody commitment unless coordinates are explicitly enacted for publication.

Ground Zero now has these candidate pilot roles:

- local reference for the common clock and standardized apparent-sunset boundary;
- reference point P for generation of the pilot Common Calendar;
- origin used by Apple Watch / phone pilot validation;
- first place against which published-calendar outputs are checked.

This does **not** automatically make a private residence the permanent national reference point of any future polity. That broader jurisdiction would require an explicit later constitutional act.

## Governing distinction

The ordinary annual vessel is always:

```
B = 364 dusk-boundaries = 52 complete weeks
```

After Day 364, annual jurisdiction is complete. Re-entry into the next ordinary year is either immediate or delayed by one complete Reconciliation interval:

```
R_n ∈ {0, 7}
K_(n+1) = K_n + 364 + R_n
```

Because both 364 and 7 are multiples of seven, the weekday sequence remains intact.

The Sun does **not** lengthen the finished year. The solar governor determines whether the next year may open immediately or after R1–R7.

## Candidate civic reference framework

- **Pilot jurisdiction:** Ground Zero / Loveland pilot.
- **Annual solar event A:** astronomical March equinox supplied by a recognized ephemeris.
- **Reference point P:** `GROUND_ZERO`, exact coordinates supplied privately at generation time.
- **Dusk protocol D:** standardized apparent sunset, Sun center approximately -0.8333 degrees.
- **Snap operator O:** `NearestLegalReentry`. Compare only the two lawful next openings: the reference sunset after 364 counted boundaries and the reference sunset seven boundaries later. Select the one closer to the next March equinox. Exact tie chooses immediate re-entry.
- **Weekday epoch:** not silently inferred. It must be explicit in the enacted first opening.
- **Civic year label:** may use the Gregorian/CE year containing the March equinox that governs that opening, without claiming a new creation-era chronology.
- **Jubilee epoch:** intentionally separate and **not enacted here**. Annual calendar adoption does not silently choose a 49/50-year Jubilee chronology.

## Publication contract

A published calendar is an evidence object, not permanent truth. Each publication must record:

- format/version identifier;
- first enacted opening;
- Ground Zero reference identity;
- nonce-protected coordinate custody digest, plus coordinates only when explicitly enacted for publication;
- dusk protocol;
- ephemeris source and input-data digest;
- snap operator;
- generation timestamp;
- generated year rows;
- SHA-256 digest of the canonical JSON bytes.

Each year row contains a 364-day ordinary year plus `reconciliationDaysAfterCompletion` equal only to 0 or 7.

The Apple Watch loader may consume a published table. It must fail closed outside the table's published range rather than extrapolate permanent authority from an expired schedule.

## Separation of jurisdictions

Ground Zero fixes the pilot comparison geometry. It does not own local human time everywhere.

A traveling watch may still show the lived day using the wearer's local apparent sunset. A published national or civic schedule, if later enacted, is generated once from its enacted reference point. These are different jobs.

## Ratification gate

The three unresolved constitutional inputs are isolated in `RATIFICATION_RECORD.md`. No generated calendar becomes canonical until those decisions are separately enacted and the promotion gates in that record pass.

## Files

- `RATIFICATION_RECORD.md` — unratified decision surface for first opening, reference point P, and equinox evidence source.
- `reference.example.json` — public shape only; real coordinates and the custody nonce belong in private runtime/generation configuration.
- `equinoxes.example.json` — ephemeris input shape.
- `published_calendar.schema.json` — publication contract.
- `../../tools/generate_common_calendar_v33.py` — deterministic generator from explicit reference + ephemeris inputs.

No exact Ground Zero street address or coordinate is committed by this candidate.

## Privacy lock

A bare SHA-256 hash of latitude/longitude is **not** treated as privacy protection because a bounded geographic search can enumerate likely coordinate pairs. The generator therefore salts the coordinate commitment with private high-entropy custody material that is never written into the publication. The publication digest is also recomputed during validation so post-generation mutation is detectable.
