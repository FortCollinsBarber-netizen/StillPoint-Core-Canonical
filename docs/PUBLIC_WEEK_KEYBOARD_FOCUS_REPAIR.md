# Public Common-week keyboard focus retention — source and browser evidence

**Classification:** public-only interactive accessibility fix, with no change to Canonical Core calendar law, manifest, receipts, protected-time interpretation or finite publication authority. The feature is a branch candidate until exact-head CI, authorized merge, post-merge public CI, Pages publication, and independent live browser tests pass.

## Demonstrated defect in the deployed public site

The existing public seven-button Common-week selector correctly changes the selected day when a focused day button receives **Enter**, but `renderWeek` rebuilt the entire button group with `replaceChildren()`. The activated button was detached without restoring focus to its replacement.

This was reproduced **in the existing live production site** over HTTPS on 2026-11-17: focus on the Friday, Common month 11/day 13, Gregorian 2026-11-13 button; press Enter; selection changes correctly, but `document.activeElement.tagName` becomes **`BODY`**. That is a real keyboard continuity loss that an automated static ARIA audit did not detect.

## Minimal fix

Within the existing published site's `renderWeek`:

1. Before rebuilding the week, record the focused button's known Core Gregorian date **only if** the currently focused element is within `#weekDays`.
2. Continue to reconstruct the same seven buttons and `aria-pressed` states from the **unchanged Core-provided year shard**, storing each button's corresponding `data-civil-date` as a DOM identity for focus recovery only.
3. If there was focus inside the group, restore focus to the button representing that same civil date. If the new Common week no longer contains it, restore focus to the newly selected Common day. Use `focus({preventScroll:true})` to avoid an unwanted page jump.
4. **Do not steal focus** from date entry, Previous/Next, the week question, or any other control. No modification is made to the Common date, day selection, or Core receipt authority.

This does not implement a new keyboard widget pattern, replace native button semantics, create auto-actions, or change tab order. All seven existing native buttons remain individually reachable using Tab; Enter/Space continue to activate them. The only change is preventing a button rebuild from dropping the user's current focus position.

## Reproducible qualification

The additive public standard-library/Node regression
`test_week_day_button_rerender_preserves_keyboard_focus_without_stealing_it`
executes the **actual production `renderWeek` and `node` functions** extracted directly from `site/stillpoint-calendar/index.html`, using a bounded minimal DOM in Node without new npm packages. It verifies first-render no-steal, actual replacement focus, the correct selected date and `aria-pressed`, `preventScroll`, external-input focus preservation, and a cross-week selected-day fallback.

Candidate exact source tests:
```sh
python -m unittest discover -s tests/calendar_core -p test_public_calendar_site_export.py -v
```
**14 of 14 tests passed** in independent execution.

An independent HTTPS Chrome candidate-browser test using the actual branch HTML and the currently published Core static source verified: pressing Enter on the Friday 2026-11-13 day button kept focus on the correct **new** Friday button after rerender; triggering a different day change while the Gregorian date input was focused left that input focused; **320 CSS px** viewport resulted in **305 px** document scroll width (no horizontal overflow).

**Evidence limits:** These are actual Chrome keyboard and scripted DOM checks. No OS screen-reader (VoiceOver/NVDA/JAWS/Orca) test was performed; the manual assisted-technology gate stays open. Green public CI does not qualify private RobertOS–StillPointOS integration.

## Nonnegotiable authority boundaries

Author-selected March 25 sacred-source anchor, selected 2027 Jubilee epoch and overlapping 49-year cycle, separate 364-day Common civil grid, and published 2026–2075 map are unchanged. Common **2076 is mathematical-only**. Public data come exclusively from the existing Canonical Core source; no private repository source, credentials, manuscripts, historical private logs, or identifying user data are used. The four private repositories **RobertOS**, **StillPointOS**, **StillPoint**, and **writing-corpus** remain private and unchanged. No billing, private runner retry, new workflow, hosting service or repository is required.
