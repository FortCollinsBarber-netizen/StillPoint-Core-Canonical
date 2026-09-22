import unittest
from datetime import date, datetime, timedelta, timezone

from stillpoint.calendar_core.dual_stamp import project_dual_stamp
from stillpoint.calendar_core.models import GeoPoint
from stillpoint.calendar_core.sunset import apparent_sunset_utc


class DualStampTests(unittest.TestCase):
    point = GeoPoint(40.3978, -105.0749, "LOVELAND_TEST")
    opening = date(2026, 1, 1)

    def stamp(self, now, *, reconciliation=0):
        return project_dual_stamp(
            now,
            location=self.point,
            local_zone="America/Denver",
            common_year=2026,
            opening_civil_date=self.opening,
            day001_weekday="Friday",
            common_standard_offset_seconds=-7 * 3600,
            reconciliation_days_after_completion=reconciliation,
            opening_continuous_k=0,
        )

    def test_observation_zero_is_day_260_not_day_1(self):
        now = datetime(2026, 9, 18, 19, 28, 57, tzinfo=timezone.utc)
        stamp = self.stamp(now)
        self.assertEqual(stamp.state, "ORDINARY")
        self.assertEqual(stamp.continuous_k, 259)
        self.assertEqual(stamp.ordinary_address, "Y_2026-260")
        self.assertIsNotNone(stamp.common_date)
        self.assertEqual(stamp.common_date.ordinal, 260)
        self.assertEqual((stamp.common_date.month, stamp.common_date.day), (9, 18))
        self.assertEqual(stamp.common_date.weekday, "Friday")
        self.assertEqual(stamp.civil_timestamp.utcoffset().total_seconds(), -6 * 3600)
        self.assertEqual(
            stamp.common_standard_timestamp.utcoffset().total_seconds(),
            -7 * 3600,
        )

    def test_reconciliation_r3_has_no_ordinary_address(self):
        boundary = apparent_sunset_utc(
            self.opening + timedelta(days=366),
            self.point,
        )
        stamp = self.stamp(boundary + timedelta(seconds=1), reconciliation=7)
        self.assertEqual(stamp.continuous_k, 366)
        self.assertEqual(stamp.state, "RECONCILIATION")
        self.assertEqual(stamp.reconciliation_day, 3)
        self.assertEqual(stamp.reconciliation_address, "Y_2026/Y_2027-R3")
        self.assertIsNone(stamp.common_date)
        self.assertIsNone(stamp.ordinary_address)

    def test_sequence_can_continue_when_annual_address_expires(self):
        boundary = apparent_sunset_utc(
            self.opening + timedelta(days=371),
            self.point,
        )
        stamp = self.stamp(boundary + timedelta(seconds=1), reconciliation=7)
        self.assertEqual(stamp.continuous_k, 371)
        self.assertEqual(stamp.state, "OUTSIDE_RANGE")
        self.assertIsNone(stamp.common_date)
        self.assertIsNone(stamp.ordinary_address)
        self.assertIsNone(stamp.reconciliation_address)

    def test_invalid_reconciliation_is_rejected(self):
        with self.assertRaises(ValueError):
            self.stamp(
                datetime(2026, 9, 18, 19, 28, 57, tzinfo=timezone.utc),
                reconciliation=1,
            )


if __name__ == "__main__":
    unittest.main()
