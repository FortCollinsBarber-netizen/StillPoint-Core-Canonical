import unittest

from stillpoint.calendar_witness import jubilee_state


class JubileeWitnessTests(unittest.TestCase):
    def test_jubilee_requires_explicit_epoch(self):
        self.assertIsNone(
            jubilee_state(common_year=2026, epoch_common_year=None)
        )

    def test_year_50_is_jubilee(self):
        state = jubilee_state(
            common_year=2075,
            epoch_common_year=2026,
            epoch_cycle=1,
        )
        self.assertTrue(state.is_jubilee_year)
        self.assertEqual(state.cycle_year, 50)


if __name__ == "__main__":
    unittest.main()
