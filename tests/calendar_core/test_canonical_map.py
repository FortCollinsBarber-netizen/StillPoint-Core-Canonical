import unittest
from datetime import date, timedelta

from stillpoint.calendar_core.canonical_map import (
    DAY001_WEEKDAY,
    FIRST_OPENING_CIVIL_DATE,
    FIRST_YEAR_LABEL,
    LAST_YEAR_LABEL,
    TOTAL_DAYS,
    YEAR_COUNT,
    address,
    address_from_continuous_offset,
    iter_fifty_year_map,
    year_opening_civil_date,
)


class CanonicalFiftyYearMapTests(unittest.TestCase):
    def test_ratified_cycle_constants(self):
        self.assertEqual(FIRST_YEAR_LABEL, 2026)
        self.assertEqual(LAST_YEAR_LABEL, 2075)
        self.assertEqual(YEAR_COUNT, 50)
        self.assertEqual(TOTAL_DAYS, 18_200)
        self.assertEqual(DAY001_WEEKDAY, "Thursday")
        self.assertEqual(
            FIRST_OPENING_CIVIL_DATE,
            date(2026, 1, 1),
        )

    def test_december30_transitions_directly_to_next_january1(self):
        last = address(
            year=2026,
            month=12,
            day=30,
        )
        nxt = address_from_continuous_offset(364)

        self.assertEqual(last.ordinal, 364)
        self.assertEqual(last.weekday, "Wednesday")
        self.assertEqual(
            (nxt.year, nxt.month, nxt.day, nxt.ordinal),
            (2027, 1, 1, 1),
        )
        self.assertEqual(nxt.weekday, "Thursday")
        with self.assertRaises(ValueError):
            address(
                year=2026,
                month=12,
                day=31,
            )

    def test_every_year_has_same_weekday_surface(self):
        for year in (2026, 2033, 2050, 2075):
            self.assertEqual(
                address(
                    year=year,
                    month=12,
                    day=10,
                ).weekday,
                "Thursday",
            )
            self.assertEqual(
                address(
                    year=year,
                    month=12,
                    day=25,
                ).weekday,
                "Friday",
            )
            self.assertEqual(
                address(
                    year=year,
                    month=11,
                    day=26,
                ).weekday,
                "Thursday",
            )

    def test_sacred_observances_have_stable_addresses(self):
        passover = address(
            year=2026,
            month=1,
            day=14,
        )
        firstfruits = address(
            year=2026,
            month=1,
            day=25,
        )
        weeks = address(
            year=2026,
            month=3,
            day=15,
        )
        atonement = address(
            year=2026,
            month=7,
            day=10,
        )

        self.assertIn("Passover", passover.observance_names)
        self.assertIn("Firstfruits", firstfruits.observance_names)
        self.assertEqual(firstfruits.weekday, "Sunday")
        self.assertIn(
            "Feast of Weeks / Pentecost",
            weeks.observance_names,
        )
        self.assertEqual(weeks.weekday, "Sunday")
        self.assertIn(
            "Day of Atonement",
            atonement.observance_names,
        )
        self.assertIn(
            "Leviticus 23:26-32",
            atonement.provenance,
        )

    def test_civic_observances_stay_fixed(self):
        christmas = address(
            year=2075,
            month=12,
            day=25,
        )
        thanksgiving = address(
            year=2075,
            month=11,
            day=26,
        )
        mothers_day = address(
            year=2075,
            month=5,
            day=10,
        )
        fathers_day = address(
            year=2075,
            month=6,
            day=21,
        )

        self.assertIn(
            "Christmas Day",
            christmas.observance_names,
        )
        self.assertEqual(christmas.weekday, "Friday")
        self.assertIn(
            "Thanksgiving Day",
            thanksgiving.observance_names,
        )
        self.assertEqual(thanksgiving.weekday, "Thursday")
        self.assertEqual(mothers_day.weekday, "Sunday")
        self.assertEqual(fathers_day.weekday, "Sunday")

    def test_enochic_seasons_and_gates_are_ordinal_layers(self):
        season_two = address_from_continuous_offset(91)
        season_three = address_from_continuous_offset(182)
        season_four = address_from_continuous_offset(273)

        self.assertEqual(
            (season_two.season, season_two.day_of_season),
            (2, 1),
        )
        self.assertEqual(
            (season_three.season, season_three.day_of_season),
            (3, 1),
        )
        self.assertEqual(
            (season_four.season, season_four.day_of_season),
            (4, 1),
        )
        self.assertIn("1 Enoch 72-82", season_four.provenance)
        self.assertTrue(1 <= season_four.enoch_gate <= 6)

    def test_jubilee_layer_reaches_year50_without_moving_grid(self):
        year50 = address(
            year=2075,
            month=1,
            day=1,
        )
        release = address(
            year=2075,
            month=7,
            day=10,
        )

        self.assertEqual(year50.jubilee_year, 50)
        self.assertTrue(year50.is_jubilee_year)
        self.assertTrue(release.is_jubilee_release_day)
        self.assertIn(
            "Leviticus 25:8-24",
            release.provenance,
        )
        self.assertIn(
            "Leviticus 25:8-13",
            release.provenance,
        )

    def test_sabbatical_thresholds_are_7_through_49(self):
        found = []
        for offset in range(50):
            year = 2026 + offset
            state = address(
                year=year,
                month=1,
                day=1,
            )
            if state.is_sabbatical_threshold:
                found.append(state.jubilee_year)
        self.assertEqual(
            found,
            [7, 14, 21, 28, 35, 42, 49],
        )

    def test_year_openings_are_exactly_364_civil_days_apart(self):
        for year in range(2026, 2075):
            self.assertEqual(
                year_opening_civil_date(year + 1)
                - year_opening_civil_date(year),
                timedelta(days=364),
            )
        self.assertEqual(
            year_opening_civil_date(2075),
            date(2074, 11, 1),
        )

    def test_full_map_has_exactly_18200_unique_addresses(self):
        addresses = list(iter_fifty_year_map())
        self.assertEqual(len(addresses), 18_200)
        self.assertEqual(
            len({item.calendar_address for item in addresses}),
            18_200,
        )
        self.assertEqual(
            addresses[0].calendar_address,
            "Y_2026-001",
        )
        self.assertEqual(
            addresses[-1].calendar_address,
            "Y_2075-364",
        )


if __name__ == "__main__":
    unittest.main()
