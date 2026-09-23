import unittest

from stillpoint.calendar_core.calendar import (
    CANONICAL_DAY001_WEEKDAY,
    MONTH_LENGTHS,
    QUARTER_DAYS,
    QUARTERS,
    common_date,
    ordinal_day,
)


class WeekIntegrityTests(unittest.TestCase):
    def test_ratified_year_is_364_days_and_52_weeks(self):
        self.assertEqual(
            MONTH_LENGTHS,
            (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 30),
        )
        self.assertEqual(sum(MONTH_LENGTHS), 364)
        self.assertEqual(364 // 7, 52)
        self.assertEqual(364 % 7, 0)
        self.assertEqual(QUARTER_DAYS, 91)
        self.assertEqual(QUARTERS, 4)
        self.assertEqual(QUARTER_DAYS * QUARTERS, 364)
        self.assertEqual(CANONICAL_DAY001_WEEKDAY, "Thursday")

    def test_december_30_is_day_364(self):
        self.assertEqual(ordinal_day(12, 30), 364)

    def test_december_31_does_not_exist(self):
        with self.assertRaises(ValueError):
            ordinal_day(12, 31)

    def test_february_29_does_not_exist(self):
        with self.assertRaises(ValueError):
            ordinal_day(2, 29)

    def test_fixed_weekday_examples(self):
        dec10 = common_date(year=1, ordinal=ordinal_day(12, 10))
        christmas = common_date(year=1, ordinal=ordinal_day(12, 25))
        self.assertEqual(dec10.weekday, "Thursday")
        self.assertEqual(christmas.weekday, "Friday")

    def test_seasonal_quarters_are_91_day_ordinal_rooms(self):
        q1_last = common_date(year=1, ordinal=91)
        q2_first = common_date(year=1, ordinal=92)
        q4_last = common_date(year=1, ordinal=364)
        self.assertEqual((q1_last.quarter, q1_last.day_of_quarter), (1, 91))
        self.assertEqual((q2_first.quarter, q2_first.day_of_quarter), (2, 1))
        self.assertEqual((q4_last.quarter, q4_last.day_of_quarter), (4, 91))

    def test_same_ordinal_keeps_same_weekday_every_year(self):
        ordinal = ordinal_day(12, 10)
        weekdays = {
            common_date(year=year, ordinal=ordinal).weekday
            for year in range(1, 51)
        }
        self.assertEqual(weekdays, {"Thursday"})

    def test_abstract_api_cannot_override_day001_weekday(self):
        with self.assertRaises(TypeError):
            common_date(
                year=1,
                ordinal=1,
                day001_weekday="Friday",
            )


if __name__ == "__main__":
    unittest.main()
