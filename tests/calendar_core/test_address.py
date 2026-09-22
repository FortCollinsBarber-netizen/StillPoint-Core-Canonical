import unittest

from stillpoint.calendar_core.address import (
    CalendarAddress,
    format_ordinary_address,
    format_reconciliation_address,
    parse_calendar_address,
)


class CalendarAddressTests(unittest.TestCase):
    def test_ordinary_round_trip(self):
        for ordinal in (1, 2, 79, 80, 363, 364):
            text = format_ordinary_address(
                2026,
                ordinal,
            )
            parsed = parse_calendar_address(text)
            self.assertEqual(
                parsed,
                CalendarAddress(
                    kind="ORDINARY",
                    year=2026,
                    ordinal=ordinal,
                ),
            )
            self.assertEqual(parsed.text, text)

    def test_reconciliation_round_trip(self):
        for r_day in range(1, 8):
            text = format_reconciliation_address(
                2026,
                r_day,
            )
            parsed = parse_calendar_address(text)
            self.assertEqual(
                parsed,
                CalendarAddress(
                    kind="RECONCILIATION",
                    year=2026,
                    reconciliation_day=r_day,
                ),
            )
            self.assertEqual(parsed.text, text)

    def test_invalid_ordinary_ordinal_fails(self):
        for ordinal in (0, 365):
            with self.assertRaises(ValueError):
                format_ordinary_address(
                    2026,
                    ordinal,
                )

    def test_invalid_reconciliation_day_fails(self):
        for r_day in (0, 8):
            with self.assertRaises(ValueError):
                format_reconciliation_address(
                    2026,
                    r_day,
                )

    def test_nonconsecutive_reconciliation_bridge_fails(self):
        with self.assertRaises(ValueError):
            parse_calendar_address(
                "Y_2026/Y_2028-R1"
            )


if __name__ == "__main__":
    unittest.main()
