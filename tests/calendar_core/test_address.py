import unittest

from stillpoint.calendar_core.address import (
    CalendarAddress,
    format_ordinary_address,
    parse_calendar_address,
)


class CalendarAddressTests(
    unittest.TestCase
):
    def test_ordinary_round_trip(self):
        for ordinal in (
            1,
            2,
            79,
            80,
            363,
            364,
        ):
            text = (
                format_ordinary_address(
                    2026,
                    ordinal,
                )
            )
            parsed = (
                parse_calendar_address(
                    text
                )
            )
            self.assertEqual(
                parsed,
                CalendarAddress(
                    year=2026,
                    ordinal=ordinal,
                ),
            )
            self.assertEqual(
                parsed.text,
                text,
            )

    def test_r_addresses_are_rejected(self):
        for value in (
            "Y_2026/Y_2027-R1",
            "Y_2026/Y_2027-R7",
        ):
            with self.assertRaises(
                ValueError
            ):
                parse_calendar_address(
                    value
                )

    def test_invalid_ordinal_fails(self):
        for ordinal in (0, 365):
            with self.assertRaises(
                ValueError
            ):
                format_ordinary_address(
                    2026,
                    ordinal,
                )


if __name__ == "__main__":
    unittest.main()
