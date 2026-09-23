import unittest
from datetime import date, datetime, timedelta, timezone

from stillpoint.calendar_core.dual_stamp import project_dual_stamp
from stillpoint.calendar_core.models import GeoPoint
class DualStampTests(unittest.TestCase):
    point = GeoPoint(40.3978, -105.0749, "LOVELAND_TEST")

    def _after_boundary(self, civil_date: date) -> datetime:
        standard = timezone(timedelta(hours=-7))
        return datetime(
            civil_date.year,
            civil_date.month,
            civil_date.day,
            0,
            0,
            1,
            tzinfo=standard,
        ).astimezone(timezone.utc)

    def _stamp(
        self,
        *,
        instant: datetime,
        common_year: int,
        opening: date,
        continuous_k: int,
    ):
        return project_dual_stamp(
            instant,
            location=self.point,
            local_zone="America/Denver",
            common_year=common_year,
            opening_civil_date=opening,
            common_standard_offset_seconds=-7 * 3600,
            continuous_k_at_opening=continuous_k,
        )

    def test_day_001_is_january_1_thursday(self):
        opening = date(2026, 1, 1)
        stamp = self._stamp(
            instant=self._after_boundary(opening),
            common_year=1,
            opening=opening,
            continuous_k=0,
        )
        self.assertEqual(stamp.state, "ORDINARY")
        self.assertEqual(stamp.calendar_address, "Y_1-001")
        self.assertEqual(
            (stamp.common_date.month, stamp.common_date.day),
            (1, 1),
        )
        self.assertEqual(stamp.common_date.weekday, "Thursday")

    def test_day_364_is_december_30(self):
        opening = date(2026, 1, 1)
        stamp = self._stamp(
            instant=self._after_boundary(
                opening + timedelta(days=363)
            ),
            common_year=1,
            opening=opening,
            continuous_k=0,
        )
        self.assertEqual(stamp.calendar_address, "Y_1-364")
        self.assertEqual(stamp.common_date.ordinal, 364)
        self.assertEqual(
            (stamp.common_date.month, stamp.common_date.day),
            (12, 30),
        )
        self.assertEqual(stamp.continuous_k, 363)

    def test_next_year_day_001_follows_after_exactly_364_days(self):
        first_opening = date(2026, 1, 1)
        next_opening = first_opening + timedelta(days=364)
        instant = self._after_boundary(next_opening)

        old_year = self._stamp(
            instant=instant,
            common_year=1,
            opening=first_opening,
            continuous_k=0,
        )
        new_year = self._stamp(
            instant=instant,
            common_year=2,
            opening=next_opening,
            continuous_k=364,
        )

        self.assertEqual(old_year.state, "OUTSIDE_RANGE")
        self.assertIsNone(old_year.calendar_address)
        self.assertEqual(old_year.continuous_k, 364)

        self.assertEqual(new_year.state, "ORDINARY")
        self.assertEqual(new_year.calendar_address, "Y_2-001")
        self.assertEqual(
            (new_year.common_date.month, new_year.common_date.day),
            (1, 1),
        )
        self.assertEqual(new_year.continuous_k, 364)
        self.assertEqual(new_year.common_date.weekday, "Thursday")

    def test_removed_reconciliation_parameter_is_not_part_of_v2_api(self):
        with self.assertRaises(TypeError):
            project_dual_stamp(
                datetime(2026, 1, 2, 0, tzinfo=timezone.utc),
                location=self.point,
                local_zone="America/Denver",
                common_year=1,
                opening_civil_date=date(2026, 1, 1),
                reconciliation_days_after_completion=7,
                common_standard_offset_seconds=-7 * 3600,
            )

    def test_translation_api_cannot_supply_weekday_epoch(self):
        with self.assertRaises(TypeError):
            project_dual_stamp(
                datetime(2026, 1, 2, 0, tzinfo=timezone.utc),
                location=self.point,
                local_zone="America/Denver",
                common_year=1,
                opening_civil_date=date(2026, 1, 1),
                day001_weekday="Friday",
                common_standard_offset_seconds=-7 * 3600,
            )


if __name__ == "__main__":
    unittest.main()
