import unittest
from datetime import date, datetime, timedelta, timezone

from stillpoint.calendar_core.dual_stamp import project_dual_stamp
from stillpoint.calendar_core.models import GeoPoint
from stillpoint.calendar_core.sunset import apparent_sunset_utc


class DualStampTests(unittest.TestCase):
    point = GeoPoint(40.3978, -105.0749, "LOVELAND_TEST")

    def _after_boundary(self, civil_date):
        return apparent_sunset_utc(civil_date, self.point) + timedelta(seconds=1)

    def _stamp(self, *, instant, opening=date(2026, 1, 1), common_year=2026, reconciliation=0, continuous_k=0):
        return project_dual_stamp(
            instant,
            location=self.point,
            local_zone="America/Denver",
            common_year=common_year,
            opening_civil_date=opening,
            day001_weekday="Thursday",
            reconciliation_days_after_completion=reconciliation,
            common_standard_offset_seconds=-7 * 3600,
            continuous_k_at_opening=continuous_k,
        )

    def test_observation_zero_projects_on_fixed_surface(self):
        stamp = self._stamp(
            instant=datetime(2026, 9, 18, 19, 28, 57, tzinfo=timezone.utc)
        )
        self.assertEqual(stamp.state, "ORDINARY")
        self.assertEqual(stamp.common_date.ordinal, 260)
        self.assertEqual((stamp.common_date.month, stamp.common_date.day), (9, 17))
        self.assertEqual(stamp.common_date.weekday, "Thursday")

    def test_day_364_is_december_30(self):
        opening = date(2026, 1, 1)
        stamp = self._stamp(instant=self._after_boundary(opening + timedelta(days=363)))
        self.assertEqual(stamp.state, "ORDINARY")
        self.assertEqual(stamp.common_date.ordinal, 364)
        self.assertEqual((stamp.common_date.month, stamp.common_date.day), (12, 30))
        self.assertEqual(stamp.calendar_address, "Y_2026-364")

    def test_any_reconciliation_request_fails_closed(self):
        with self.assertRaises(ValueError):
            self._stamp(
                instant=datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
                reconciliation=7,
            )

    def test_next_year_reuses_continuous_k_without_gap(self):
        next_opening = date(2026, 12, 31)
        instant = self._after_boundary(next_opening)
        old = self._stamp(instant=instant)
        new = self._stamp(
            instant=instant,
            opening=next_opening,
            common_year=2027,
            continuous_k=364,
        )
        self.assertEqual(old.state, "OUTSIDE_RANGE")
        self.assertEqual(old.continuous_k, 364)
        self.assertEqual(new.state, "ORDINARY")
        self.assertEqual(new.common_date.ordinal, 1)
        self.assertEqual((new.common_date.month, new.common_date.day), (1, 1))
        self.assertEqual(new.common_date.weekday, "Thursday")
        self.assertEqual(new.continuous_k, 364)


if __name__ == "__main__":
    unittest.main()
