# Civic Clock for Apple Watch

Civic Clock is the Apple Watch surface for the StillPoint common clock and calendar.

## What this first build does

- Shows ordinary civil clock time without pretending clock time defines the lived day.
- Computes the local StillPoint day boundary from standardized apparent sunset (Sun center about -0.8333 degrees).
- Names the dusk-to-dusk day correctly: after Friday sunset, the watch is already in Saturday / Sabbath.
- Shows the next local sunset and the remaining time until the boundary.
- Marks Sabbath as Friday-sunset through Saturday-sunset.
- Publishes a WidgetKit complication for glanceable common-calendar state.
- Stores the most recent solar/calendar snapshot in an App Group so the complication does not independently request location.
- Refuses to invent the unresolved national epoch / official published year table. Until a canonical table is supplied, the app displays the civil clock + solar boundary + weekly identity and marks the annual StillPoint date as pending.

## Why this is not a literal third-party watch face

Apple exposes complications and shareable configurations built from Apple watch faces. The supported implementation is therefore:

1. a native watchOS app;
2. WidgetKit complications;
3. later, a shareable Apple watch-face configuration that includes those complications.

The full-screen watch app is the "Civic Clock" experience. The complication makes the common calendar visible from an Apple watch face.

## Canonical rules represented

- The clock is a translation layer; local apparent sunset defines the lived/calendar day boundary.
- A week is seven successive dusk boundaries.
- Saturday / Sabbath runs from Friday sunset to Saturday sunset.
- The ordinary annual vessel is 364 days / 52 weeks.
- Reconciliation is a whole-week transition and must never create an isolated leftover day.
- The national epoch and published reconciliation schedule are intentionally configuration data, not guessed in code.

## Project generation

This folder includes an XcodeGen `project.yml`. With XcodeGen installed:

```bash
cd clients/apple-watch/CivicClock
xcodegen generate
open CivicClock.xcodeproj
```

In Xcode:

1. Select your Apple Developer team for both targets.
2. Change the bundle identifiers if needed.
3. Add the App Group `group.com.stillpoint.civicclock` to the Watch app and Widget extension.
4. Run the Watch app once and grant When In Use location access.
5. Add the Civic Clock complication to a compatible Apple watch face.

No location is uploaded by this build. The last coordinate and rendered snapshot are stored locally in the shared App Group.

## Next locked input

A future canonical `published_calendar.json` should provide the enacted epoch and prospective year-opening / Reconciliation schedule. This first build will not manufacture those values.
