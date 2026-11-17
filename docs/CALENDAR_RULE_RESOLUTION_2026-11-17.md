# StillPoint rollover and sacred-year author-selected working resolution

**Originating author:** Robert Emmanuel LaDay  
**Prepared:** November 17, 2026  
**Status:** author-selected working rules, November 17, 2026; not an ancient prescription, civil enactment, or governmental authority.

## The rollover resolution

Count consecutive 49-year blocks. The fiftieth-year proclamation overlaps Year
1 of the next block rather than inserting another year into each recurrence.
Store the cycle coordinate and the proclamation coordinate separately. Keep
seven-year and priestly-course counting continuous through the proclamation.

| Common year | Cycle position | Proclamation position |
|---|---|---|
| 2027 | Cycle 1, Year 1 | Origin, not a release event |
| 2033 | Cycle 1, Year 7 | First seventh-year threshold |
| 2075 | Cycle 1, Year 49 | Seven sevens completed |
| 2076 | Cycle 2, Year 1 | Ordinal Year 50 following Cycle 1 |
| 2125 | Cycle 3, Year 1 | Next proclamation, 49 years later |
| 2321 | Cycle 7, Year 1 | Sixth proclamation; 294 years elapsed |

2027 is author-selected as the explicit working planning epoch, rather than
inferred from the publication's first year. The standalone-50 counter remains
available by name for comparison. It is not mixed into this default model.

Leviticus 25:8–13 supplies seven sevens, a sacred fiftieth year and the Atonement
proclamation; historical rollover interpretations differ. Jubilees uses
seven-times-seven chronology. Bartos (2023), footnote 27, explicitly discusses
the overlapping first/fiftieth interpretation and its Second Temple use. The
choice is coherent with the selected architecture, without claiming a universal
resolution of every tradition's exegesis.

## The sacred-year anchor

Preserve 30/30/31 source months and a Wednesday opening as a separate overlay.
Do not equate scriptural month numbers with civil month names.

The author-selected working rule is **source Month 1 Day 1 = Common March 25**, always
Wednesday. It was the first Wednesday after the March 20 equinox in the 2026
reference year. This is a disclosed one-time project convention. The Sun does
not subsequently move the anchor or insert days. A strict 364-day year drifts
relative to seasons, so this profile does not promise continuous spring
alignment or fulfill every seasonal reading of Abib in Deuteronomy 16.

Other Wednesdays would preserve the same internal arithmetic. No ancient text
can uniquely select a date in the new Common Calendar. Robert Emmanuel LaDay selected March 25 on November 17, 2026 as the
working StillPoint source-calendar anchor. This subsequent decision is not
attributed retroactively to any ancient community or the September manuscript.
Other communities' religious calendars remain independent.

## Feast projection

Retain the project's declared Firstfruits interpretation: the Sunday after the
weekly Sabbath following Unleavened Bread. With this source geometry it is
I/26; counting it as Day 1 produces III/15 as Day 50. This is one stated
interpretation, not a rule imposed on other communities.

| Appointment | Source | Common | Weekday |
|---|---|---|---|
| Sacred opening | I/1 | March 25 | Wednesday |
| Passover | I/14 | April 7 | Tuesday |
| Unleavened Bread begins | I/15 | April 8 | Wednesday |
| Firstfruits | I/26 | April 19 | Sunday |
| Weeks | III/15 | June 7 | Sunday |
| Trumpets | VII/1 | September 23 | Wednesday |
| Atonement / proclamation appointment | VII/10 | October 2 | Friday |
| Booths begins | VII/15 | October 7 | Wednesday |
| Eighth-day assembly | VII/22 | October 14 | Wednesday |

A date is not an astronomical instant. Sunset-based sacred observance,
including Leviticus 23:32's evening boundary, remains separately identified.
This table does not silently enact midnight release, change civic twilight
protection or discharge an obligation.

## Implementation and limits

Python and Watch consume the same exported profile and cycle policy. The
Watch counter no longer uses publication row index as Jubilee year. Its loader
checks source-to-Common projection metadata; religious labels identify their
StillPoint profile. Schematic month markers are not asserted to be new moons.

The nine layers, civil geometry, clock and original publication remain intact.
The 2026–2075 map does not authorize a 2076 payload. A publication extension is
separate from calculating the first author-selected working proclamation year.

Checks include every source day; 4,732 Common dates across 13 years; fixed
weekdays; inclusive Firstfruits counting; both counter models; six proclamation
boundaries over 294 years; no-epoch states; and finite coverage. Earlier tests
and behavior remain preserved in Git. Fixtures are regenerated from code.

## Public evidence

- Leviticus 25: https://bible.usccb.org/bible/leviticus/25
- Leviticus 23: https://bible.usccb.org/bible/leviticus/23
- Exodus 12: https://bible.usccb.org/bible/exodus/12
- Deuteronomy 16: https://bible.usccb.org/bible/deuteronomy/16
- VanderKam's translated Jubilees selections, especially chapters 6 and 50:
  https://www.posenlibrary.com/entry/festivals-and-calendar-controversy
- Segal's Wednesday-start 30/30/31 tables and discussion of competing readings:
  https://www.thetorah.com/article/jewish-calendar-in-jubilees-a-solar-year
- Bartos (2023), especially footnote 27. Selected relevant passages inspected;
  no direct ancient-manuscript collation claimed:
  https://journals.sagepub.com/doi/full/10.1177/0142064X231191176
- USNO 2026 seasons:
  https://aa.usno.navy.mil/calculated/seasons?year=2026&tz=8&tz_sign=-1&tz_label=false&dst=true&submit=Get+Data

No original manuscript is rewritten or reproduced. Implementing a project
profile establishes neither universal religious authority nor governmental law.
