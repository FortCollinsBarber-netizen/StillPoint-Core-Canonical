from __future__ import annotations

import unittest

from stillpoint.calendar_core.calendar import (
    MONTH_LENGTHS,
    common_date,
    month_day_from_ordinal,
    ordinal_day,
)


GREGORIAN_COMMON_MONTH_LENGTHS = (
    31, 28, 31, 30, 31, 30,
    31, 31, 30, 31, 30, 31,
)


class CalendarConstitutionLockTests(unittest.TestCase):
    def test_only_december_31_is_removed_from_the_familiar_common_year(self):
        differences = [
            (month, old, new)
            for month, (old, new) in enumerate(
                zip(GREGORIAN_COMMON_MONTH_LENGTHS, MONTH_LENGTHS),
                start=1,
            )
            if old != new
        ]
        self.assertEqual(differences, [(12, 31, 30)])
        self.assertEqual(sum(MONTH_LENGTHS), 364)

    def test_january_1_through_december_30_are_preserved_in_order(self):
        ordinal = 0
        for month, length in enumerate(MONTH_LENGTHS, start=1):
            for day in range(1, length + 1):
                ordinal += 1
                self.assertEqual(ordinal_day(month, day), ordinal)
                self.assertEqual(month_day_from_ordinal(ordinal), (month, day))
        self.assertEqual(ordinal, 364)
        self.assertEqual(month_day_from_ordinal(1), (1, 1))
        self.assertEqual(month_day_from_ordinal(364), (12, 30))

    def test_seed_rhythm_is_locked(self):
        expected = {
            (1, 1): "Thursday",
            (7, 4): "Saturday",
            (10, 31): "Saturday",
            (11, 26): "Thursday",
            (12, 10): "Thursday",
            (12, 24): "Thursday",
            (12, 25): "Friday",
            (12, 30): "Wednesday",
        }
        for (month, day), weekday in expected.items():
            value = common_date(
                year=2026,
                ordinal=ordinal_day(month, day),
            )
            self.assertEqual(
                value.weekday,
                weekday,
                msg=f"{month:02d}-{day:02d}",
            )

    def test_every_named_date_keeps_the_same_weekday_for_all_fifty_years(self):
        seed = {
            ordinal: common_date(year=2026, ordinal=ordinal).weekday
            for ordinal in range(1, 365)
        }
        for year in range(2026, 2076):
            for ordinal, weekday in seed.items():
                value = common_date(year=year, ordinal=ordinal)
                self.assertEqual(
                    value.weekday,
                    weekday,
                    msg=f"year={year} ordinal={ordinal}",
                )

    def test_every_year_closes_wednesday_and_reopens_thursday(self):
        for year in range(2026, 2075):
            last = common_date(year=year, ordinal=364)
            nxt = common_date(year=year + 1, ordinal=1)
            self.assertEqual((last.month, last.day), (12, 30))
            self.assertEqual(last.weekday, "Wednesday")
            self.assertEqual((nxt.month, nxt.day), (1, 1))
            self.assertEqual(nxt.weekday, "Thursday")

    def test_no_hidden_intercalary_date_can_enter_the_named_grid(self):
        with self.assertRaises(ValueError):
            ordinal_day(2, 29)
        with self.assertRaises(ValueError):
            ordinal_day(12, 31)
        with self.assertRaises(ValueError):
            month_day_from_ordinal(365)


if __name__ == "__main__":
    unittest.main()
