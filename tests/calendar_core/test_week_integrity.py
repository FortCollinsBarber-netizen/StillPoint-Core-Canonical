import unittest

from stillpoint.calendar_core.calendar import (
    MONTH_LENGTHS,
    QUARTER_LENGTHS,
    common_date,
    ordinal_day,
)


class WeekIntegrityTests(
    unittest.TestCase
):
    def test_ratified_year_is_364_days_and_52_weeks(self):
        self.assertEqual(
            MONTH_LENGTHS,
            (
                31, 28, 31,
                30, 31, 30,
                31, 31, 30,
                31, 30, 30,
            ),
        )
        self.assertEqual(
            sum(MONTH_LENGTHS),
            364,
        )
        self.assertEqual(
            364 // 7,
            52,
        )
        self.assertEqual(
            364 % 7,
            0,
        )
        self.assertEqual(
            QUARTER_LENGTHS,
            (90, 91, 92, 91),
        )

    def test_december_30_is_day_364(self):
        self.assertEqual(
            ordinal_day(12, 30),
            364,
        )

    def test_december_31_does_not_exist(self):
        with self.assertRaises(ValueError):
            ordinal_day(12, 31)

    def test_february_29_does_not_exist(self):
        with self.assertRaises(ValueError):
            ordinal_day(2, 29)

    def test_fixed_weekday_examples(self):
        # Ratified fixed-grid anchor used for map construction:
        # Jan 1 Thursday -> Dec 10 Thursday -> Dec 25 Friday.
        dec10 = common_date(
            year=2026,
            ordinal=ordinal_day(
                12,
                10,
            ),
            day001_weekday="Thursday",
        )
        christmas = common_date(
            year=2026,
            ordinal=ordinal_day(
                12,
                25,
            ),
            day001_weekday="Thursday",
        )
        self.assertEqual(
            dec10.weekday,
            "Thursday",
        )
        self.assertEqual(
            christmas.weekday,
            "Friday",
        )

    def test_same_ordinal_keeps_same_weekday_every_year(self):
        ordinal = ordinal_day(
            12,
            10,
        )
        weekdays = {
            common_date(
                year=year,
                ordinal=ordinal,
                day001_weekday=
                    "Thursday",
            ).weekday
            for year in range(
                2026,
                2076,
            )
        }
        self.assertEqual(
            weekdays,
            {"Thursday"},
        )


if __name__ == "__main__":
    unittest.main()
