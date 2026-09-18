import unittest

from stillpoint.calendar_core.jubilee import jubilee_state


class JubileeTests(unittest.TestCase):
    def test_no_hidden_epoch(self):
        self.assertIsNone(jubilee_state(common_year=2026, epoch_common_year=None))

    def test_seven_sevens_then_fiftieth_year(self):
        thresholds = []
        for year in range(2026, 2026 + 49):
            state = jubilee_state(common_year=year, epoch_common_year=2026)
            if state.is_sabbatical_threshold:
                thresholds.append(state.cycle_year)
        self.assertEqual(thresholds, [7, 14, 21, 28, 35, 42, 49])

        jubilee = jubilee_state(common_year=2026 + 49, epoch_common_year=2026)
        self.assertTrue(jubilee.is_jubilee_year)
        self.assertEqual(jubilee.cycle_year, 50)


if __name__ == "__main__":
    unittest.main()
