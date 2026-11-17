from __future__ import annotations

import unittest

from stillpoint.calendar_core.calendar import common_date, ordinal_day
from stillpoint.calendar_core.jubilee import jubilee_state, jubilee_release_gate
from stillpoint.calendar_core.long_cycles import JubileeConfiguration
from stillpoint.calendar_core.observances import SACRED_OBSERVANCES, MONTH_OPENINGS
from stillpoint.calendar_core.runtime_surface import calendar_day_payload, load_enacted_publication
from stillpoint.calendar_core.sacred import (
    SacredYearProfile, common_from_sacred, sacred_from_common,
    sacred_ordinal, sacred_month_day, PROFILE_STATUS,
)


class SacredProfileTests(unittest.TestCase):
    def test_source_months_are_separate_from_named_civil_months(self):
        with self.assertRaises(ValueError):
            sacred_ordinal(1, 31)
        self.assertEqual(ordinal_day(1, 31), 31)
        self.assertEqual(sacred_ordinal(3, 31), 91)
        self.assertEqual(sacred_ordinal(12, 31), 364)
        for value in (0, 365, True):
            with self.assertRaises(ValueError):
                sacred_month_day(value)

    def test_all_source_days_round_trip_across_civil_year_boundary(self):
        for ordinal in range(1, 365):
            month, day = sacred_month_day(ordinal)
            projected = common_from_sacred(2026, month, day)
            recovered = sacred_from_common(projected.year, projected.month, projected.day)
            self.assertEqual((recovered["year"], recovered["month"], recovered["day"]),
                             (2026, month, day))
        closing = common_from_sacred(2026, 12, 31)
        self.assertEqual((closing.year, closing.month, closing.day), (2027, 3, 24))

    def test_every_common_day_round_trips_across_thirteen_years(self):
        for year in range(2026, 2039):
            for ordinal in range(1, 365):
                civil = common_date(year=year, ordinal=ordinal)
                source = sacred_from_common(year, civil.month, civil.day)
                recovered = common_from_sacred(source["year"], source["month"], source["day"])
                self.assertEqual((recovered.year, recovered.ordinal), (year, ordinal))

    def test_source_year_and_quarters_open_on_wednesday(self):
        for month in (1, 4, 7, 10):
            self.assertEqual(common_from_sacred(2027, month, 1).weekday, "Wednesday")
        with self.assertRaises(ValueError):
            SacredYearProfile(anchor_common_month=1, anchor_common_day=1)
        start = common_from_sacred(2027, 1, 1)
        self.assertEqual((start.month, start.day), (3, 25))

    def test_declared_feasts_have_independent_source_and_common_addresses(self):
        expected = {
            "passover": ((1, 14), (4, 7), "Tuesday"),
            "unleavened-bread": ((1, 15), (4, 8), "Wednesday"),
            "firstfruits": ((1, 26), (4, 19), "Sunday"),
            "weeks": ((3, 15), (6, 7), "Sunday"),
            "trumpets": ((7, 1), (9, 23), "Wednesday"),
            "atonement": ((7, 10), (10, 2), "Friday"),
            "booths": ((7, 15), (10, 7), "Wednesday"),
            "eighth-day": ((7, 22), (10, 14), "Wednesday"),
        }
        for item in SACRED_OBSERVANCES:
            source, civil, weekday = expected[item.id]
            self.assertEqual((item.source_month, item.source_day), source)
            self.assertEqual((item.month, item.day), civil)
            self.assertEqual(common_date(year=2027, ordinal=item.start_ordinal).weekday, weekday)

    def test_firstfruits_count_is_fifty_days_inclusive(self):
        start = common_from_sacred(2027, 1, 26)
        finish = common_from_sacred(2027, 3, 15)
        self.assertEqual(finish.ordinal - start.ordinal + 1, 50)
        self.assertEqual((start.weekday, finish.weekday), ("Sunday", "Sunday"))

    def test_month_markers_are_not_claimed_to_be_astronomical_new_moons(self):
        self.assertEqual(len(MONTH_OPENINGS), 12)
        for item in MONTH_OPENINGS:
            self.assertIn("not a claim of an astronomical new moon", item.note)
            self.assertEqual(item.source_day, 1)

    def test_release_gate_dual_stamps_source_month_seven(self):
        gate = jubilee_release_gate(common_year=2076, epoch_common_year=2027)
        self.assertEqual((gate.month, gate.day), (7, 10))
        self.assertEqual(gate.ordinal, 192)
        self.assertEqual(gate.common_month_day, (10, 2))
        self.assertEqual(gate.common_ordinal, ordinal_day(10, 2))

    def test_first_and_second_proclamations_share_next_cycle_year_one(self):
        for year, cycle, completed in ((2076, 2, 1), (2125, 3, 2), (2174, 4, 3)):
            value = jubilee_state(common_year=year, epoch_common_year=2027)
            self.assertEqual((value.cycle, value.cycle_year), (cycle, 1))
            self.assertEqual(value.proclamation_ordinal_year, 50)
            self.assertEqual(value.completed_cycle, completed)
            self.assertTrue(value.is_jubilee_year)
        ordinary = jubilee_state(common_year=2077, epoch_common_year=2027)
        self.assertEqual(ordinary.cycle_year, 2)
        self.assertFalse(ordinary.is_jubilee_year)

    def test_standalone_fifty_remains_explicitly_available_for_comparison(self):
        first = jubilee_state(common_year=2076, epoch_common_year=2027, rollover_rule="standalone-50")
        following = jubilee_state(common_year=2077, epoch_common_year=2027, rollover_rule="standalone-50")
        self.assertEqual((first.cycle, first.cycle_year), (1, 50))
        self.assertEqual((following.cycle, following.cycle_year), (2, 1))
        self.assertTrue(first.is_jubilee_year)

    def test_six_overlapping_proclamations_complete_the_294_year_phase(self):
        returns = [year for year in range(2028, 2322)
                   if jubilee_state(common_year=year, epoch_common_year=2027).is_jubilee_year]
        self.assertEqual(returns, [2076, 2125, 2174, 2223, 2272, 2321])
        self.assertEqual(returns[-1] - 2027, 294)
        self.assertEqual(((294 * 52) % 24, 294 % 7), (0, 0))

    def test_author_selected_working_rule_does_not_claim_public_enactment(self):
        value = calendar_day_payload(2027, ordinal_day(4, 19))
        self.assertEqual(value["sacred_year_profile"]["selectionStatus"], PROFILE_STATUS)
        self.assertEqual(PROFILE_STATUS, "author-selected-working-rule-not-civil-enactment")
        self.assertEqual(value["sacred_year_profile"]["selectedBy"], "Robert Emmanuel LaDay")
        self.assertEqual(value["sacred_year_profile"]["selectedOn"], "2026-11-17")
        self.assertEqual(value["long_cycle_policy"]["selectedBy"], "Robert Emmanuel LaDay")
        self.assertEqual(value["long_cycle_policy"]["selectedOn"], "2026-11-17")
        self.assertEqual(value["long_cycle_policy"]["selectionStatus"], PROFILE_STATUS)
        source = next(x for x in value["observances"] if x["id"] == "firstfruits")
        self.assertEqual(source["source_coordinate"]["month"], 1)
        self.assertEqual(source["source_coordinate"]["day"], 26)
        self.assertEqual(value["sacred_date"]["ordinal"], 26)
        self.assertFalse(value["sacred_year_profile"]["gridAuthority"])

    def test_release_uses_profile_observance_not_literal_common_july_ten(self):
        configuration = JubileeConfiguration(epoch_common_year=2026)
        old = calendar_day_payload(2075, ordinal_day(7, 10), jubilee_configuration=configuration)
        correct = calendar_day_payload(2075, ordinal_day(10, 2), jubilee_configuration=configuration)
        self.assertFalse(old["jubilee"]["is_jubilee_release_day"])
        self.assertTrue(correct["jubilee"]["is_jubilee_release_day"])
        with self.assertRaises(ValueError):
            calendar_day_payload(2076, 1)
        self.assertEqual(len(load_enacted_publication()["years"]), 50)


if __name__ == "__main__":
    unittest.main()
