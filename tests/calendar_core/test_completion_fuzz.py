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

        for _ in range(4000):
            year = rng.randint(-5000, 12000)
            ordinal = rng.randint(1, 364)

            text = format_ordinary_address(year, ordinal)
            parsed = parse_calendar_address(text)
            self.assertEqual(parsed.year, year)
            self.assertEqual(parsed.ordinal, ordinal)
            self.assertEqual(parsed.text, text)

            projected = common_date(year=year, ordinal=ordinal)
            self.assertEqual(
                ordinal_day(projected.month, projected.day),
                ordinal,
            )
            self.assertTrue(1 <= projected.quarter <= 4)
            self.assertTrue(1 <= projected.day_of_quarter <= 91)
            self.assertTrue(1 <= projected.week <= 52)
            self.assertTrue(1 <= projected.day_in_week <= 7)

    def test_month_grid_fuzz_never_exceeds_364(self):
        rng = random.Random(520007)
        for _ in range(2000):
            month = rng.randint(1, 12)
            day = rng.randint(1, MONTH_LENGTHS[month - 1])
            self.assertTrue(1 <= ordinal_day(month, day) <= 364)

    def test_r_addresses_never_parse(self):
        for r_day in range(1, 8):
            with self.assertRaises(ValueError):
                parse_calendar_address(f"Y_1/Y_2-R{r_day}")


if __name__ == "__main__":
    unittest.main()
