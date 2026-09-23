import unittest

from stillpoint.calendar_core.calendar import (
    DAY001_WEEKDAY,
    MONTH_LENGTHS,
    month_day_from_ordinal,
    ordinal_day,
    weekday_for_ordinal,
)
from stillpoint.calendar_core.sacred_map import (
    address_for,
    build_sacred_civic_map,
    resolved_observances,
)


class SacredCivicMapTests(unittest.TestCase):
    def test_fixed_grid_is_exactly_364_days_and_52_weeks(self):
        self.assertEqual(sum(MONTH_LENGTHS), 364)
        self.assertEqual(364 // 7, 52)
        self.assertEqual(DAY001_WEEKDAY, "Thursday")
        self.assertEqual(month_day_from_ordinal(364), (12, 30))
        with self.assertRaises(ValueError):
            ordinal_day(12, 31)

    def test_ratified_weekday_anchors_repeat(self):
        self.assertEqual(
            weekday_for_ordinal(ordinal_day(12, 10)),
            "Thursday",
        )
        self.assertEqual(
            weekday_for_ordinal(ordinal_day(12, 25)),
            "Friday",
        )
        self.assertEqual(
            weekday_for_ordinal(ordinal_day(7, 4)),
            "Saturday",
        )

    def test_enochic_quarters_are_ordinal_geometry_not_civic_month_lengths(self):
        document = build_sacred_civic_map()
        self.assertEqual(document["sourceArchitecture"]["quarterDays"], 91)
        self.assertEqual(document["sourceArchitecture"]["quarters"], 4)
        self.assertEqual(
            document["sourceArchitecture"]["enochPhaseLengths"],
            [30, 30, 31] * 4,
        )
        self.assertEqual(
            [row["ordinal"] for row in document["annualTemplate"] if row["quarterDay"] == 91],
            [91, 182, 273, 364],
        )

    def test_biblical_appointments_resolve_onto_fixed_surface(self):
        by_id = {item.id: item for item in resolved_observances()}
        self.assertEqual((by_id["passover"].month, by_id["passover"].day), (1, 14))
        self.assertEqual((by_id["firstfruits"].month, by_id["firstfruits"].day), (1, 18))
        self.assertEqual(by_id["firstfruits"].weekday, "Sunday")
        self.assertEqual((by_id["weeks"].month, by_id["weeks"].day), (3, 8))
        self.assertEqual(by_id["weeks"].weekday, "Sunday")
        self.assertEqual((by_id["atonement"].month, by_id["atonement"].day), (7, 10))

    def test_civic_recurrences_are_frozen_not_recomputed_by_external_calendar(self):
        by_id = {item.id: item for item in resolved_observances()}
        self.assertEqual((by_id["mlk-day"].month, by_id["mlk-day"].day), (1, 19))
        self.assertEqual((by_id["mothers-day"].month, by_id["mothers-day"].day), (5, 10))
        self.assertEqual((by_id["fathers-day"].month, by_id["fathers-day"].day), (6, 21))
        self.assertEqual((by_id["thanksgiving"].month, by_id["thanksgiving"].day), (11, 26))

    def test_fifty_year_map_layers_jubilee_without_moving_annual_grid(self):
        document = build_sacred_civic_map(first_year=1)
        self.assertEqual(len(document["years"]), 50)
        thresholds = [
            row["cycleYear"]
            for row in document["years"]
            if row["isSabbaticalThreshold"]
        ]
        self.assertEqual(thresholds, [7, 14, 21, 28, 35, 42, 49])
        self.assertTrue(document["years"][-1]["isJubileeYear"])
        self.assertEqual(
            document["years"][-1]["jubileeReleaseGateOrdinal"],
            ordinal_day(7, 10),
        )

    def test_address_returns_full_query_surface(self):
        row = address_for(year=50, month=12, day=25)
        self.assertEqual(row["ordinal"], 359)
        self.assertEqual(row["week"], 52)
        self.assertEqual(row["weekday"], "Friday")
        self.assertIn("christmas", row["observances"])
        self.assertTrue(row["jubilee"]["isJubileeYear"])
        self.assertIn("enochGate", row)
        self.assertIn("provenance", row)


if __name__ == "__main__":
    unittest.main()
