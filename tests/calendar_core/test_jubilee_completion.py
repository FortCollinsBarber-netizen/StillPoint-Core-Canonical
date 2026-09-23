import unittest

from stillpoint.calendar_core import build_calendar_core_spec
from stillpoint.calendar_core.jubilee import (
    jubilee_release_gate,
    jubilee_state,
)


class JubileeCompletionTests(unittest.TestCase):
    def test_missing_epoch_fails_closed(self):
        self.assertIsNone(
            jubilee_state(common_year=1, epoch_common_year=None)
        )
        self.assertIsNone(
            jubilee_release_gate(common_year=1, epoch_common_year=None)
        )

    def test_seven_sabbatical_thresholds_end_at_year_49(self):
        thresholds = []
        for year in range(1, 50):
            state = jubilee_state(
                common_year=year,
                epoch_common_year=1,
            )
            if state.is_sabbatical_threshold:
                thresholds.append(state.cycle_year)
        self.assertEqual(thresholds, [7, 14, 21, 28, 35, 42, 49])

    def test_year_50_is_jubilee_and_has_atonement_release_gate(self):
        state = jubilee_state(common_year=50, epoch_common_year=1)
        self.assertTrue(state.is_jubilee_year)
        self.assertEqual(state.cycle_year, 50)
        gate = jubilee_release_gate(common_year=50, epoch_common_year=1)
        self.assertIsNotNone(gate)
        self.assertEqual((gate.month, gate.day), (7, 10))
        self.assertEqual(gate.name, "Day of Atonement")

    def test_year_after_jubilee_reenters_next_cycle_year_one(self):
        state = jubilee_state(common_year=51, epoch_common_year=1)
        self.assertEqual(state.cycle, 2)
        self.assertEqual(state.cycle_year, 1)
        self.assertFalse(state.is_jubilee_year)

    def test_jubilee_never_rewrites_annual_law(self):
        before = build_calendar_core_spec()
        for common_year in range(1, 101):
            jubilee_state(
                common_year=common_year,
                epoch_common_year=1,
            )
            jubilee_release_gate(
                common_year=common_year,
                epoch_common_year=1,
            )
        after = build_calendar_core_spec()
        self.assertEqual(before, after)
        self.assertEqual(after["ordinaryCalendar"]["baseYearDays"], 364)
        self.assertEqual(after["ordinaryCalendar"]["weeksPerYear"], 52)
        self.assertFalse(after["annualTransition"]["reconciliationAllowed"])
        self.assertEqual(after["annualTransition"]["interannualDays"], 0)


if __name__ == "__main__":
    unittest.main()
