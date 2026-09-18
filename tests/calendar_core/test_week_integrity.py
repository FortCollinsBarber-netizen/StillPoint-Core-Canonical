import unittest

from stillpoint.calendar_core.calendar import MONTH_LENGTHS, common_date, ordinal_day


class WeekIntegrityTests(unittest.TestCase):
    def test_year_and_quarters_are_whole_weeks(self):
        self.assertEqual(sum(MONTH_LENGTHS), 364)
        self.assertEqual(364 % 7, 0)
        for q in range(0, 12, 3):
            self.assertEqual(sum(MONTH_LENGTHS[q:q + 3]), 91)
            self.assertEqual(91 % 7, 0)

    def test_fixed_weekday_examples_from_pilot(self):
        dec10 = common_date(
            year=2026,
            ordinal=ordinal_day(12, 10),
            day001_weekday="Friday",
        )
        christmas = common_date(
            year=2026,
            ordinal=ordinal_day(12, 25),
            day001_weekday="Friday",
        )
        self.assertEqual(dec10.weekday, "Thursday")
        self.assertEqual(christmas.weekday, "Friday")


if __name__ == "__main__":
    unittest.main()
