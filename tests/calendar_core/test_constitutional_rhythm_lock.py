from __future__ import annotations

from datetime import date
import unittest

from stillpoint.calendar_core.calendar import (
    CANONICAL_DAY001_WEEKDAY,
    CANONICAL_MONTH_LENGTHS,
    MONTH_LENGTHS,
    common_date,
    ordinal_day,
)
from stillpoint.calendar_core.gates import phase_for_base_day
from stillpoint.calendar_core.jubilee import jubilee_state
from stillpoint.calendar_core.observances import (
    CIVIC_OBSERVANCES,
    SACRED_OBSERVANCES,
)
from stillpoint.calendar_core.runtime_surface import (
    calendar_day_payload,
    load_enacted_publication,
)


class ConstitutionalRhythmLockTests(unittest.TestCase):
    """Hard regression lock for the enacted repeating annual rhythm.

    These tests protect the minimal-disruption correction itself. They do not
    make astronomical or observational witness data constitutional authority.
    """

    def test_only_december_31_is_removed_from_familiar_named_date_sequence(self):
        self.assertEqual(
            CANONICAL_MONTH_LENGTHS,
            (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 30),
        )
        self.assertEqual(MONTH_LENGTHS, CANONICAL_MONTH_LENGTHS)
        self.assertEqual(sum(MONTH_LENGTHS), 364)

        named_dates = [
            (month, day)
            for month, length in enumerate(MONTH_LENGTHS, start=1)
            for day in range(1, length + 1)
        ]
        self.assertEqual(len(named_dates), 364)
        self.assertEqual(named_dates[0], (1, 1))
        self.assertEqual(named_dates[-1], (12, 30))
        self.assertIn((1, 31), named_dates)
        self.assertIn((10, 31), named_dates)
        self.assertNotIn((2, 29), named_dates)
        self.assertNotIn((12, 31), named_dates)

    def test_2026_template_anchors_are_permanent(self):
        self.assertEqual(CANONICAL_DAY001_WEEKDAY, "Thursday")
        anchors = {
            (1, 1): "Thursday",
            (12, 10): "Thursday",
            (12, 24): "Thursday",
            (12, 25): "Friday",
            (12, 30): "Wednesday",
        }
        for year in range(2026, 2076):
            for (month, day), weekday in anchors.items():
                projected = common_date(
                    year=year,
                    ordinal=ordinal_day(month, day),
                )
                self.assertEqual(
                    projected.weekday,
                    weekday,
                    (year, month, day),
                )

    def test_familiar_2026_civic_rhythm_repeats_for_all_50_years(self):
        # These are named-date/weekday anchors on the frozen annual template.
        # They are not claims that an external legal calendar has already
        # adopted StillPoint.
        template = {
            (1, 1): "Thursday",
            (1, 19): "Monday",
            (2, 14): "Saturday",
            (3, 17): "Tuesday",
            (4, 3): "Friday",
            (4, 5): "Sunday",
            (5, 10): "Sunday",
            (5, 25): "Monday",
            (6, 19): "Friday",
            (6, 21): "Sunday",
            (7, 4): "Saturday",
            (9, 7): "Monday",
            (10, 31): "Saturday",
            (11, 11): "Wednesday",
            (11, 26): "Thursday",
            (12, 24): "Thursday",
            (12, 25): "Friday",
            (12, 30): "Wednesday",
        }
        for year in range(2026, 2076):
            for (month, day), weekday in template.items():
                self.assertEqual(
                    common_date(
                        year=year,
                        ordinal=ordinal_day(month, day),
                    ).weekday,
                    weekday,
                    (year, month, day),
                )

    def test_same_named_date_never_migrates_weekdays_across_50_year_map(self):
        for month, length in enumerate(MONTH_LENGTHS, start=1):
            for day in range(1, length + 1):
                ordinal = ordinal_day(month, day)
                weekdays = {
                    common_date(year=year, ordinal=ordinal).weekday
                    for year in range(2026, 2076)
                }
                self.assertEqual(
                    len(weekdays),
                    1,
                    (month, day, weekdays),
                )

    def test_each_year_is_exactly_52_complete_weeks(self):
        for year in range(2026, 2076):
            first = common_date(year=year, ordinal=1)
            last = common_date(year=year, ordinal=364)
            self.assertEqual(first.weekday, "Thursday")
            self.assertEqual(last.weekday, "Wednesday")
            self.assertEqual(first.week, 1)
            self.assertEqual(last.week, 52)
            self.assertEqual(last.day_in_week, 7)

    def test_friday_sabbath_sunday_rhythm_is_stable(self):
        # One arbitrary annual run proves the repeating weekly sequence;
        # the 50-year loop proves it never shifts by year.
        for year in range(2026, 2076):
            friday = common_date(
                year=year,
                ordinal=ordinal_day(9, 25),
            )
            sabbath = common_date(
                year=year,
                ordinal=ordinal_day(9, 26),
            )
            sunday = common_date(
                year=year,
                ordinal=ordinal_day(9, 27),
            )
            self.assertEqual(
                (friday.weekday, sabbath.weekday, sunday.weekday),
                ("Friday", "Saturday", "Sunday"),
            )

    def test_enacted_publication_is_one_364_day_template_repeated_50_times(self):
        document = load_enacted_publication()
        rows = document["years"]

        self.assertEqual(len(rows), 50)
        self.assertEqual(int(rows[0]["year"]), 2026)
        self.assertEqual(int(rows[-1]["year"]), 2075)

        # openingCivilDate is retained only as a host/ISO interoperability
        # translation. It is not the Common Calendar's named-date coordinate.
        openings = [
            date.fromisoformat(str(row["openingCivilDate"]))
            for row in rows
        ]
        for left, right in zip(openings, openings[1:]):
            self.assertEqual((right - left).days, 364)

        first_2027 = calendar_day_payload(2027, 1)
        self.assertEqual(
            first_2027["canonical_coordinate"]["label"],
            "2027-01-01",
        )
        self.assertEqual(
            first_2027["canonical_coordinate"]["weekday"],
            "Thursday",
        )
        self.assertEqual(
            first_2027["interop_window"]["opens"],
            "2026-12-31",
        )
        self.assertFalse(
            first_2027["interop_window"]["mutates_calendar"]
        )

        self.assertEqual(50 * 364, 18_200)

    def test_seasons_and_enochic_gate_positions_repeat_without_year_input(self):
        # Seasonal/gate architecture is a function of immutable ordinal
        # position, not an external civil year label.
        checkpoints = (1, 31, 61, 92, 122, 152, 183, 213, 243, 274, 304, 334, 364)
        baseline = {
            ordinal: phase_for_base_day(ordinal)
            for ordinal in checkpoints
        }
        for year in range(2026, 2076):
            for ordinal, phase in baseline.items():
                projected = common_date(year=year, ordinal=ordinal)
                self.assertEqual(projected.ordinal, ordinal)
                again = phase_for_base_day(projected.ordinal)
                self.assertEqual(again, phase)

    def test_sacred_and_civic_observance_weekdays_do_not_migrate(self):
        for observance in SACRED_OBSERVANCES + CIVIC_OBSERVANCES:
            ordinal = ordinal_day(observance.month, observance.day)
            weekdays = {
                common_date(year=year, ordinal=ordinal).weekday
                for year in range(2026, 2076)
            }
            self.assertEqual(
                len(weekdays),
                1,
                (observance.id, weekdays),
            )

    def test_seven_year_49_and_jubilee_positions_run_on_same_calendar_surface(self):
        thresholds = []
        for year in range(2026, 2075):
            state = jubilee_state(
                common_year=year,
                epoch_common_year=2026,
            )
            self.assertIsNotNone(state)
            if state.is_sabbatical_threshold:
                thresholds.append(state.cycle_year)

        self.assertEqual(thresholds, [7, 14, 21, 28, 35, 42, 49])

        jubilee = jubilee_state(
            common_year=2075,
            epoch_common_year=2026,
        )
        self.assertIsNotNone(jubilee)
        self.assertEqual(jubilee.cycle_year, 50)
        self.assertTrue(jubilee.is_jubilee_year)

        # The annual address beneath Jubilee is still the same Thursday Jan 1
        # and the same Wednesday Dec 30; the larger cycle does not mutate it.
        self.assertEqual(
            common_date(year=2075, ordinal=1).weekday,
            "Thursday",
        )
        self.assertEqual(
            common_date(year=2075, ordinal=364).weekday,
            "Wednesday",
        )

    def test_invalid_extra_dates_fail_closed(self):
        with self.assertRaises(ValueError):
            ordinal_day(2, 29)
        with self.assertRaises(ValueError):
            ordinal_day(12, 31)


if __name__ == "__main__":
    unittest.main()
