import unittest
from datetime import date, datetime, timedelta, timezone

from stillpoint.calendar_core.dual_stamp import project_dual_stamp
from stillpoint.calendar_core.models import GeoPoint
from stillpoint.calendar_core.sunset import apparent_sunset_utc


class DualStampTests(unittest.TestCase):
    point = GeoPoint(40.3978, -105.0749, "LOVELAND_TEST")

    def test_observation_zero_is_day_260_not_day_1(self):
        now = datetime(2026, 9, 18, 19, 28, 57, tzinfo=timezone.utc)
        stamp = project_dual_stamp(
            now,
            location=self.point,
            local_zone="America/Denver",
            common_year=2026,
            opening_civil_date=date(2026, 1, 1),
            day001_weekday="Friday",
            common_standard_offset_seconds=-7 * 3600,
        )
        self.assertEqual(stamp.continuous_k, 259)
        self.assertEqual(stamp.state, "ORDINARY")
        self.assertIsNotNone(stamp.common_date)
        self.assertEqual(stamp.common_date.ordinal, 260)
        self.assertEqual((stamp.common_date.month, stamp.common_date.day), (9, 18))
        self.assertEqual(stamp.common_date.quarter, 3)
        self.assertEqual(stamp.common_date.week, 38)
        self.assertEqual(stamp.common_date.weekday, "Friday")
        self.assertIsNone(stamp.reconciliation_address)
        self.assertEqual(stamp.civil_timestamp.utcoffset().total_seconds(), -6 * 3600)
        self.assertEqual(stamp.common_standard_timestamp.utcoffset().total_seconds(), -7 * 3600)

    def test_reconciliation_r3_has_no_ordinary_address(self):
        opening = date(2026, 1, 1)
        r3_boundary = apparent_sunset_utc(opening + timedelta(days=366), self.point)
        stamp = project_dual_stamp(
            r3_boundary + timedelta(seconds=1),
            location=self.point,
            local_zone="America/Denver",
            common_year=2026,
            opening_civil_date=opening,
            day001_weekday="Friday",
            reconciliation_days_after_completion=7,
            common_standard_offset_seconds=-7 * 3600,
        )
        self.assertEqual(stamp.continuous_k, 366)
        self.assertEqual(stamp.state, "RECONCILIATION")
        self.assertEqual(stamp.reconciliation_day, 3)
        self.assertEqual(stamp.reconciliation_address, "Y_2026/Y_2027-R3")
        self.assertIsNone(stamp.common_date)


if __name__ == "__main__":
    unittest.main()
