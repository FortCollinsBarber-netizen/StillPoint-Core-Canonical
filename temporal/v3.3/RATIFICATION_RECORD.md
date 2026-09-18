# StillPoint Temporal v3.3 — Ratification Record

**Status:** UNRATIFIED  
**Authority:** Robert Emmanuel LaDay, sole human CEO / final ratifying authority  
**Purpose:** Separate the three remaining constitutional inputs required before StillPoint Temporal v3.3 may generate a canonical `published_calendar.json`.

This record is a decision surface, not a decision. Technical success, passing CI, a working Apple Watch client, or a successful forecast does not ratify any option below.

## Already settled by the v3.3 candidate

These items are not reopened by this record:

- the ordinary annual vessel completes after **364 standardized local dusk-boundaries / 52 complete weeks**;
- a Reconciliation interval, when required, is **interannual** and may contain only **0 or 7** dusk-boundaries;
- Reconciliation does not retroactively convert the completed ordinary year into a 371-day year;
- the seven-day week is continuous;
- the local lived day and a national/civic annual reference are separate jurisdictions;
- Ground Zero is the private Loveland pilot origin and is **not** automatically the national Reference Rule point;
- the Jubilee epoch is a separate jurisdiction and is not enacted by annual-calendar ratification;
- v3.2 remains preserved as historical locked authority. v3.3 is a successor if ratified, not an in-place rewrite.

The candidate recurrence remains:

```
B = 364
R_n ∈ {0, 7}
K_(n+1) = K_n + B + R_n
```

The three decisions below must be ratified separately.

---

## Decision 1 — First enacted Common Calendar opening

### Question

What event establishes the first legally enacted opening boundary from which prospective Common Calendar year labels are counted?

The exact civil date cannot be finalized independently of Decision 2 (reference point) and Decision 3 (equinox evidence), because the lawful opening is a standardized sunset boundary selected relative to the governing March equinox.

### Option 1A — Prospective first lawful opening after ratification

Enact the first Common Calendar year at the first lawful v3.3 opening generated after the ratification instrument takes effect.

**Consequence:** avoids retroactively relabeling already-lived days; the public calendar begins where authority actually begins. Historical dates remain dual-stamped historical data rather than newly legislated Common Calendar dates.

**Custody effect:** simplest provenance chain. Ratification time, source ephemeris, reference point, first opening, and first publication can be linked without back-casting authority.

### Option 1B — Predeclared modern epoch

Enact a named modern year (for example a specified March-equinox season) as Year 1 even if the ratification record is executed later.

**Consequence:** creates a stable modern anchor for pilots and public explanation but requires an explicit rule distinguishing retrospective labels from authority that did not yet exist.

**Custody effect:** the publication must mark pre-ratification rows as reconstructed calendar coordinates, not evidence that v3.3 was legally operative at that time.

### Option 1C — Historical epoch

Choose a historical civil, religious, national, astronomical, or textual event as Year 1 and generate the system backward and forward from it.

**Consequence:** produces a deeper chronology but imports historical-interpretive questions into an otherwise prospective civic mechanism.

**Custody effect:** requires much stronger provenance, historical-calendar conversion rules, and explicit treatment of uncertainty. A historical label must not silently become a claim about ancient practice.

### Ratification field

```
FIRST_OPENING_OPTION = UNRATIFIED
FIRST_YEAR_LABEL     = UNRATIFIED
EFFECTIVE_RULE       = UNRATIFIED
RATIFIED_BY          = UNRATIFIED
RATIFIED_AT          = UNRATIFIED
```

No generator may infer these values.

---

## Decision 2 — National / civic Reference Rule point P

### Question

Which enacted geodetic point supplies the single comparison geometry used to determine whether prospective re-entry occurs immediately after Day 364 or after R1–R7?

This point performs one bounded job. It does not determine every locality's lived sunset.

### Option 2A — Ground Zero

Use the private Loveland pilot origin as the enacted national/civic reference.

**Consequence:** maximum continuity between pilot testing and publication geometry.

**Boundary cost:** a private residence would acquire public calendrical jurisdiction. That would reverse the present privacy/locality boundary and therefore requires an explicit constitutional act. The exact address must never enter the public repository merely because the point is chosen.

### Option 2B — Fixed public astronomical / civic point

Enact one permanent, publicly documented geodetic coordinate associated with an appropriate public site or legally defined civic marker.

**Consequence:** reproducible, inspectable, and independent of a private person's residence.

**Boundary cost:** choosing a public site is a civic convention, not an astronomical discovery. The instrument must state why that point has comparison jurisdiction and how relocation or institutional closure is handled without silently moving P.

### Option 2C — Defined geographic/geodetic center

Use a formally specified center computed from a named territory and method.

**Consequence:** avoids privileging a private address or existing institution.

**Boundary cost:** "center" is not self-defining. Different methods and territorial changes can move the point. The method, territorial dataset, datum, and version would all require custody.

### Option 2D — Other explicitly enacted coordinate

Ratify any other fixed geodetic point together with a written jurisdictional rationale.

**Consequence:** preserves design freedom while preventing an implicit or accidental reference point.

### Ratification field

```
REFERENCE_POINT_OPTION = UNRATIFIED
REFERENCE_POINT_ID     = UNRATIFIED
PUBLIC_COORDINATES     = UNRATIFIED
GEODETIC_DATUM         = UNRATIFIED
CHANGE_RULE            = UNRATIFIED
RATIFIED_BY            = UNRATIFIED
RATIFIED_AT            = UNRATIFIED
```

Until this decision is enacted, Ground Zero remains local pilot authority only.

---

## Decision 3 — Recognized March-equinox evidence source

### Question

Which astronomical source has evidentiary jurisdiction to supply the governing March-equinox instants used by `NearestLegalReentry`?

The source supplies evidence. It does not own the week, the epoch, or the reference point.

### Option 3A — U.S. Naval Observatory Astronomical Applications Department as primary source

Use the USNO Earth's Seasons data service / API as the primary published source of March-equinox UTC instants.

**Evidence:** USNO's Astronomical Applications Department publishes an official Earth's Seasons service covering 1700–2100, including equinox and solstice times, and provides an API for machine-readable season data.

Official references:

- https://aa.usno.navy.mil/data/Earth_Seasons
- https://aa.usno.navy.mil/data/api
- https://aa.usno.navy.mil/about/mission

**Consequence:** direct, public, government-operated season timestamps with a simple machine interface.

**Limit:** the currently published service has a stated 1700–2100 range. A calendar published beyond its evidentiary horizon needs a successor source/version or a new ratification of the evidence layer.

### Option 3B — JPL Horizons-derived equinoxes as primary source

Use NASA/JPL Horizons output and a documented root-finding procedure for the geocentric apparent ecliptic longitude of the Sun.

**Evidence:** the Horizons manual states that, for Earth, seasonal boundaries are determined using the **geocentric apparent ecliptic longitude of the Sun** and directs users to observer quantity #31 from the geocenter for Earth seasons.

Official reference:

- https://ssd.jpl.nasa.gov/horizons/manual.html

**Consequence:** high-quality ephemeris infrastructure and a calculation path that exposes the underlying seasonal coordinate.

**Limit:** the publication pipeline becomes more complex because the Common Calendar must preserve the exact Horizons query configuration, sampling/root-finding method, reference frame choices, and resulting input digest.

### Option 3C — Primary source plus independent comparator

Ratify one source as legally operative evidence and a second authoritative source as an audit comparator.

Example structure:

```
PRIMARY    = USNO Earth's Seasons API
COMPARATOR = JPL Horizons geocentric apparent solar ecliptic longitude
```

**Consequence:** disagreements become visible without creating two simultaneous governors. The primary source decides the published schedule; the comparator audits it.

**Boundary rule:** a comparator discrepancy cannot silently rewrite an already-open year. It creates a review event for future publication under the continuing-evidence architecture.

### Ratification field

```
EPHEMERIS_OPTION        = UNRATIFIED
PRIMARY_SOURCE_ID       = UNRATIFIED
PRIMARY_SOURCE_VERSION  = UNRATIFIED
COMPARATOR_SOURCE_ID    = UNRATIFIED
DISCREPANCY_RULE        = UNRATIFIED
PUBLICATION_HORIZON     = UNRATIFIED
RATIFIED_BY             = UNRATIFIED
RATIFIED_AT             = UNRATIFIED
```

The generator must ingest evidence bytes and preserve their SHA-256 digest. It must not manufacture missing equinox instants.

---

## Independence rule

Ratifying one decision does not ratify the others.

For example:

- selecting USNO does not choose a national reference point;
- selecting a reference point does not choose Year 1;
- selecting a first opening does not enact a Jubilee epoch;
- Ground Zero's pilot use does not create national jurisdiction;
- a successful generated schedule does not ratify the inputs that produced it.

## Promotion gate

Temporal v3.3 may move from **CANDIDATE** to **LOCKED TEMPORAL AUTHORITY** only after all three decision blocks above are complete and the resulting implementation passes:

1. deterministic generation from the ratified inputs;
2. schema validation;
3. publication SHA-256 verification;
4. proof that every ordinary year contains exactly 364 counted dusk-boundaries;
5. proof that every Reconciliation interval is exactly 0 or 7 boundaries;
6. proof that the continuous weekday sequence is never interrupted;
7. long-range prospective stress testing over the ratified evidence horizon;
8. Apple Watch / client fail-closed tests inside and outside the published range;
9. custody verification showing the exact ratification record, evidence inputs, generator revision, and publication digest.

Only after those gates pass may the canonical Watch stop displaying `ANNUAL TABLE PENDING`.

## Ratification

This section remains intentionally blank until Robert Emmanuel LaDay expressly enacts each decision.

```
DECISION 1 — FIRST OPENING:       UNRATIFIED
DECISION 2 — REFERENCE POINT P:   UNRATIFIED
DECISION 3 — EQUINOX EVIDENCE:    UNRATIFIED

TEMPORAL v3.3 STATUS:              CANDIDATE
CANONICAL CALENDAR PUBLICATION:    NONE
```
