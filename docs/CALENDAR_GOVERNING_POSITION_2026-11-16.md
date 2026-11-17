# StillPoint — Governing 364-Day Calendar Position

**Author and final human authority:** Robert Emmanuel LaDay  
**Declaration date:** 2026-11-16  
**Status:** Author-directed governing statement; documentation proposal for review.  
**Relationship to the existing 2026-09-23 ratification:** Confirms the immutable 364-date civil surface and limits on observational overlays. This statement does not silently amend runtime code, historical artifacts, or prior frozen releases. Any operational implementation difference is separately identified for review.

## Clear Statement Going Forward

God said 364 days is the complete year.  
That is the position we will hold.

We will no longer treat the 364-day year as a system that must be continuously adjusted to the tropical year in order to remain valid. The attempt to force the correct calendar to behave like the broken one is what created the confusion. That ends here.

## Settled Positions

1. **The year is 364 days.** Exactly 52 weeks. Four seasons of 91 days. Festivals and Sabbaths remain fixed relative to one another. This is the order received in the Enochic and Jubilees traditions and treated as perfect.

2. **The nested cycles remain.**
   - 6-year priestly rotation
   - 49-year Jubilee
   - 294-year return of the combined cycles

   These are internal resets of the schematic system. They do not require, and do not claim, continuous seasonal tracking.

3. **Seasonal drift is real and is not a defect in the 364-day year.** The tropical year is longer. Over time the seasons will move relative to the fixed 364-day dates. That is a fact about the physical Earth. It does not make the 364-day year imperfect. The year is perfect as the received structure of sacred and civil time. The seasons are an external reality that the calendar does not have to own.

4. **We stop trying to reconcile the two by intercalation inside the calendar.** No more searching for a hidden leap-week rule that the texts never clearly give. No more treating the 294-year numerical near-match to 293 tropical years as a secret correction mechanism. Those were attempts to make the correct calendar serve the broken one.

## Practical Solutions for StillPoint

### A. Fixed Civil Surface

Adopt a permanently repeating 364-day civil calendar as the underlying coordinate system.

- 364 numbered days.
- 52 weeks.
- Fixed weekday for every date.
- No December 31. No February 29.
- January 1 (or the first day of the year) remains fixed on the same weekday forever.

This is the calendar. It does not change.

### B. Observational Overlay (Not Part of the Calendar)

Keep a separate, non-authoritative layer that simply reports where the actual equinoxes, solstices, and agricultural seasons currently fall relative to the fixed 364-day dates.

This layer has no power to insert days, shift festivals, or alter the civil surface. It only informs. People, communities, and institutions can use that information for farming, planning, or liturgy if they choose. The calendar itself remains untouched.

### C. Jubilee and Release Remain Calendar-Driven

The 49-year and 294-year cycles continue to function as the recurring points at which claims are examined and, where appropriate, released.

These are acts of structural mercy inside the fixed system. They do not depend on the seasons being in the “right” place on the 364-day grid. Release is a jurisdictional act, not an agricultural one.

### D. No Claim of Continuous Astronomical Perfection

We state openly: the 364-day year is perfect as the received order of time. It is not a continuously accurate tropical calendar. Those are two different things. Confusing them produced the earlier errors. We will not confuse them again.

## What This Protects

- The integrity of the 364-day revelation.
- The fixed relationship of Sabbath and festival.
- The nested cycles of priestly service, sabbatical, and Jubilee.
- The principle that legitimate authority must have endpoints and release points.
- The refusal to let modern solar-year anxiety rewrite the received structure.

We are no longer trying to fix the perfect year so that it matches a drifting Earth. We receive the 364-day year as given, run the civil and sacred order on that surface, and treat the seasons as an external reality that can be observed without being allowed to alter the calendar.

**That is the settled position.**

---

## Repository custody and implementation boundary (editorial note; not part of the author's declaration)

- The existing enacted `docs/CALENDAR_RATIFICATION_364.md`, `stillpoint/contracts/calendar_ratification_v1.json`, and `specs/temporal_calendar/CALENDAR_LOCKDOWN_2026.md` already fix 364 named dates, weekday continuity, no leap days, and witness overlays with no grid authority.
- The existing named civil surface preserves January 1–December 30 and the 2026 weekday template. This statement does **not** automatically replace that naming system with the historical 30/30/31 Enochic month arrangement.
- **Separate implementation discrepancy requiring human review:** `stillpoint/calendar_core/jubilee.py` currently advances its Jubilee cycle using `years_since // 50` and `years_since % 50`, returning a Year-50 release gate. The author’s governing position here specifies 49-year Jubilee reckoning and a 294-year combined recurrence. The relationship of a Year-50 proclamation/release gate to 49-year cycle counting must be explicitly specified in a separately authorized design change before modifying implementation. Do not infer or silently patch that behavior.
- The 6-year priestly-course cycle and 294-year return are source/theory declarations in this document; no claim is made here that the current Calendar Core implements those computations.
- Superseded 364/371 and astronomical-reconciliation rules remain historical lineage only. No code, contracts, tests, release records, or canonical date geometry are modified by this documentary record.

**Provenance:** User-authored declaration supplied directly in the StillPoint conversation on 2026-11-16; repository custody transcription preserves the original governing substance.