import random
import unittest

from stillpoint.calendar_core.address import (
    format_ordinary_address,
    format_reconciliation_address,
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

            r_day = rng.randint(1, 7)
            r_text = format_reconciliation_address(year, r_day)
            r_parsed = parse_calendar_address(r_text)
            self.assertEqual(r_parsed.kind, "RECONCILIATION")
            self.assertIsNone(r_parsed.ordinal)
            self.assertEqual(r_parsed.reconciliation_day, r_day)

    def test_month_grid_fuzz_never_exceeds_364(self):
        rng = random.Random(520007)
        for _ in range(1000):
            month = rng.randint(1, 12)
            day = rng.randint(1, MONTH_LENGTHS[month - 1])
            self.assertTrue(1 <= ordinal_day(month, day) <= 364)


if __name__ == "__main__":
    unittest.main()
