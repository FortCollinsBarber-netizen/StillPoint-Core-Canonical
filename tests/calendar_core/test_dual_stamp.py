import unittest
from datetime import date, datetime, timedelta, timezone

from stillpoint.calendar_core.dual_stamp import project_dual_stamp
from stillpoint.calendar_core.models import GeoPoint
from stillpoint.calendar_core.service import CalendarConfig, get_calendar_snapshot
from stillpoint.calendar_core.sunset import apparent_sunset_utc


class DualStampTests(unittest.TestCase):
    point = GeoPoint(
        40.3978,
        -105.0749,
        "LOVELAND_TEST",
    )

    def _stamp(
        self,
        *,
        instant: datetime,
        common_year: int = 2026,
        opening: date = date(2026, 1, 1),
        reconciliation: int = 0,
        continuous_k: int = 0,
        year_count: int = 50,
    ):
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
            year_count=year_count,
        )

    def _after_boundary(
        self,
        civil_date: date,
    ) -> datetime:
        return (
            apparent_sunset_utc(
                civil_date,
                self.point,
            )
            + timedelta(seconds=1)
        )

    def test_observation_zero_preserves_continuous_day_count(self):
        now = datetime(
            2026,
            9,
            18,
            19,
            28,
            57,
            tzinfo=timezone.utc,
        )
        stamp = self._stamp(instant=now)
        self.assertEqual(stamp.continuous_k, 259)
        self.assertEqual(stamp.state, "ORDINARY")
        self.assertEqual(stamp.calendar_address, "Y_2026-260")
        self.assertEqual(stamp.common_date.ordinal, 260)
        self.assertEqual(
            (stamp.common_date.month, stamp.common_date.day),
            (9, 17),
        )
        self.assertEqual(stamp.common_date.weekday, "Thursday")
        self.assertIsNone(stamp.reconciliation_address)
        self.assertEqual(
            stamp.civil_timestamp.utcoffset().total_seconds(),
            -6 * 3600,
        )
        self.assertEqual(
            stamp.common_standard_timestamp.utcoffset().total_seconds(),
            -7 * 3600,
        )

    def test_day_364_rolls_directly_to_next_year_day_001(self):
        opening = date(2026, 1, 1)
        last = self._stamp(
            instant=self._after_boundary(
                opening + timedelta(days=363)
            ),
            opening=opening,
        )
        nxt = self._stamp(
            instant=self._after_boundary(
                opening + timedelta(days=364)
            ),
            opening=opening,
        )

        self.assertEqual(last.calendar_address, "Y_2026-364")
        self.assertEqual(last.common_date.ordinal, 364)
        self.assertEqual(
            (last.common_date.month, last.common_date.day),
            (12, 30),
        )
        self.assertEqual(last.common_date.weekday, "Wednesday")

        self.assertEqual(nxt.calendar_address, "Y_2027-001")
        self.assertEqual(nxt.common_date.year, 2027)
        self.assertEqual(nxt.common_date.ordinal, 1)
        self.assertEqual(
            (nxt.common_date.month, nxt.common_date.day),
            (1, 1),
        )
        self.assertEqual(nxt.common_date.weekday, "Thursday")
        self.assertEqual(nxt.continuous_k, 364)

    def test_reconciliation_input_fails_closed(self):
        with self.assertRaisesRegex(
            ValueError,
            "Reconciliation is not part",
        ):
            self._stamp(
                instant=self._after_boundary(
                    date(2026, 12, 31)
                ),
                reconciliation=7,
            )

    def test_fifty_year_map_has_no_gap_or_extra_day(self):
        opening = date(2026, 1, 1)
        last_offset = (364 * 50) - 1
        last = self._stamp(
            instant=self._after_boundary(
                opening + timedelta(days=last_offset)
            )
        )
        outside = self._stamp(
            instant=self._after_boundary(
                opening + timedelta(days=last_offset + 1)
            )
        )

        self.assertEqual(last.common_date.year, 2075)
        self.assertEqual(last.common_date.ordinal, 364)
        self.assertEqual(last.calendar_address, "Y_2075-364")
        self.assertEqual(outside.state, "OUTSIDE_RANGE")
        self.assertIsNone(outside.common_date)
        self.assertIsNone(outside.calendar_address)

    def test_snapshot_jubilee_follows_projected_year(self):
        opening = date(2026, 1, 1)
        year_50_opening = opening + timedelta(days=364 * 49)
        instant = self._after_boundary(year_50_opening)

        snapshot = get_calendar_snapshot(
            instant,
            config=CalendarConfig(
                location=self.point,
                local_zone="America/Denver",
                common_year=2026,
                opening_civil_date=opening,
                day001_weekday="Thursday",
                common_standard_offset_seconds=-7 * 3600,
                jubilee_epoch_common_year=2026,
                year_count=50,
            ),
        )
        self.assertEqual(snapshot.common_date.year, 2075)
        self.assertEqual(snapshot.jubilee.cycle_year, 50)
        self.assertTrue(snapshot.jubilee.is_jubilee_year)

    def test_before_k_epoch_has_no_continuous_k_or_address(self):
        opening = date(2026, 1, 1)
        stamp = self._stamp(
            instant=self._after_boundary(
                opening - timedelta(days=1)
            ),
            opening=opening,
            continuous_k=0,
        )
        self.assertEqual(stamp.state, "OUTSIDE_RANGE")
        self.assertIsNone(stamp.continuous_k)
        self.assertIsNone(stamp.calendar_address)

    def test_negative_k_anchor_fails_closed(self):
        with self.assertRaises(ValueError):
            self._stamp(
                instant=datetime(
                    2026,
                    1,
                    1,
                    12,
                    tzinfo=timezone.utc,
                ),
                continuous_k=-1,
            )


if __name__ == "__main__":
    unittest.main()
