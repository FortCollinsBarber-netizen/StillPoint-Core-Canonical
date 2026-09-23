import random
import unittest

from stillpoint.calendar_core.address import (
    format_ordinary_address,
    parse_calendar_address,
)
from stillpoint.calendar_core.calendar import (
    MONTH_LENGTHS,
    common_date,
    ordinal_day,
)


class CompletionFuzzTests(unittest.TestCase):
    def test_deterministic_address_and_calendar_fuzz(self):
        rng = random.Random(364007)
        weekdays = [
            "Sunday", "Monday", "Tuesday", "Wednesday",
            "Thursday", "Friday", "Saturday",
        ]

        for _ in range(2000):
            year = rng.randint(-5000, 12000)
            ordinal = rng.randint(1, 364)
            weekday = rng.choice(weekdays)

            text = format_ordinary_address(year, ordinal)
            parsed = parse_calendar_address(text)
            self.assertEqual(parsed.year, year)
            self.assertEqual(parsed.ordinal, ordinal)
            self.assertEqual(parsed.text, text)

            projected = common_date(
                year=year,
                ordinal=ordinal,
                day001_weekday=weekday,
            )
            self.assertEqual(
                ordinal_day(projected.month, projected.day),
                ordinal,
            )
            self.assertTrue(1 <= projected.quarter <= 4)
            self.assertTrue(1 <= projected.week <= 52)
            self.assertTrue(1 <= projected.day_in_week <= 7)

    def test_month_grid_is_exactly_364_and_has_no_december_31(self):
        self.assertEqual(
            MONTH_LENGTHS,
            (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 30),
        )
        self.assertEqual(sum(MONTH_LENGTHS), 364)
        with self.assertRaises(ValueError):
            ordinal_day(12, 31)

    def test_month_grid_fuzz_never_exceeds_364(self):
        rng = random.Random(520007)
        for _ in range(1000):
            month = rng.randint(1, 12)
            day = rng.randint(1, MONTH_LENGTHS[month - 1])
            self.assertTrue(1 <= ordinal_day(month, day) <= 364)


if __name__ == "__main__":
    unittest.main()
