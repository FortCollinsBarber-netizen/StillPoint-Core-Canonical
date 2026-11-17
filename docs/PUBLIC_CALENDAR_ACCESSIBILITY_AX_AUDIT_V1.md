# Public Common Calendar — accessible navigation and Chrome AX audit

**Status:** public-safe candidate; *not* a live release until full exact-head Core CI, public browser export, authorized merge, post-merge Pages success and a fresh live-browser check.

**Authority and preservation:** Work only from public Canonical Core `c8fe576d01e609d1e189737a62822b198a24e568`. No changes to calendar math, Common year limits, source coordinates, Jubilee overlays, Python Core, exporter or receipt schemas. The four private repositories remain private and untouched. This document does not assert any actual VoiceOver, NVDA, JAWS or Orca session was run.

## Specific finding and correction

A 2026-11-17 automated **axe-core v4.10.3** accessibility audit on the live public page reported **zero detected WCAG 2 A / AA, 2.1 AA, 2.2 AA or best-practice violations**, but returned **three inconclusive `aria-prohibited-attr` nodes**: generic `div` controls labeled `Civil-date navigation`, `Choose a day from this Common week` and `Download independently reproducible read-only receipts`. These ARIA labels are not reliably exposed on otherwise unnamed generic containers. They were changed in the existing site HTML to explicit `role="group"` with each original label unchanged.

Keyboard users now also get a **first-tab “Skip to calendar content” link**. The link is visually offscreen until focused, then appears in the viewport with a visible focus border, and targets the unique `<main id="mainContent" tabindex="-1>` landmark. The main region retains a visible focus outline. No focus trap, automatic scroll loop, or new JavaScript is introduced.

The page continues to use the browser's existing date picker and text fields. Receipt files still remain on the device; downloads and calendar reads remain bounded and static. No role or group claims any consent, identity or execution authority.

## Evidence from actual Chrome accessibility tree and keyboard

In a separate isolated **HTTPS browser** using the candidate HTML and real, SHA-checked live Core data:

- Initial focused element: `BODY`; first **Tab** focused the exact **Skip to calendar content** link. Its bounding rectangle began at **top 12px** and was fully visible rather than offscreen.
- **Enter** activated that link and moved focus to `MAIN#mainContent` with URL fragment `#mainContent`.
- Chrome DevTools Protocol `Accessibility.getFullAXTree` showed three **non-ignored `group` nodes** with their exact intended accessible names. The accessibility tree also exposed the skip link and main landmark.
- **axe-core v4.10.3** again found **zero detected WCAG-tagged/best-practice violations** and **no `aria-prohibited-attr` inconclusive cases**. It reported **27 inconclusive color-contrast checks**, because axe cannot infer a uniform background from the existing CSS gradients. Do *not* represent these as 27 proven contrast failures, or as a fully certified color-contrast audit.
- A bounded sRGB check of explicit foreground/background endpoint samples gave **8.95:1** white header text against the brighter dark-blue gradient endpoint; **6.39:1** header-eyebrow text against that endpoint; **6.88:1** header subtitle text; **6.01:1** muted text against the very light panel endpoint; and **3.93:1** focus-border contrast against white. These samples help review, but do not replace pixel-level audits at all gradient positions.
- At **320 CSS px** viewport the document scroll width was **305px**, without horizontal overflow.

**This is not an actual OS-level screen reader test.** No VoiceOver, NVDA, JAWS or Orca executable is available in this browser test session. Chrome's accessibility-tree checks prove the browser exposes the semantics, not that every screen reader announces them correctly. A human screen-reader pass remains open and must not be marked completed.

## Reproducible regression and release gate

The existing public exporter test suite has one additive executable `test_accessible_navigation_and_named_control_groups_are_in_actual_export` that parses the **real exported HTML** using only Python's standard `html.parser` and verifies:

- exactly one target main landmark, main focusability and exactly one matching skip link before the header;
- all three named `role="group"` containers and **zero** leftover generic labeled `div` containers;
- the skip link appears onscreen on keyboard focus and the main focus indicator exists in the built artifact.

This test uses no new workflow, paid service, browser dependency, private source or uploaded user data. After branch qualification, validate on the **actual published Pages URL** with keyboard and browser accessibility-tree checks. A source-only or pre-merge green test does not prove deployment.

A future assisted manual pass should exercise the skip link, Common week controls, receipt buttons, async status text, the file-inspector result, the bounded 2076 refusal, and the non-action authority explanation with VoiceOver/Safari and NVDA/Firefox or Chrome. Record the assistive-technology version and exact OS/browser, and file only demonstrated failures—do not claim that manual acceptance has already occurred.
