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
        reconciliation: int = 7,
        continuous_k: int = 0,
    ):
        return project_dual_stamp(
            instant,
            location=self.point,
            local_zone="America/Denver",
            common_year=common_year,
            opening_civil_date=opening,
            day001_weekday="Friday",
            reconciliation_days_after_completion=
                reconciliation,
            common_standard_offset_seconds=
                -7 * 3600,
            continuous_k_at_opening=
                continuous_k,
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

    def test_observation_zero_is_day_260_not_day_1(self):
        now = datetime(
            2026,
            9,
            18,
            19,
            28,
            57,
            tzinfo=timezone.utc,
        )
        stamp = self._stamp(
            instant=now,
            reconciliation=0,
        )
        self.assertEqual(
            stamp.continuous_k,
            259,
        )
        self.assertEqual(
            stamp.state,
            "ORDINARY",
        )
        self.assertEqual(
            stamp.calendar_address,
            "Y_2026-260",
        )
        self.assertIsNotNone(
            stamp.common_date
        )
        self.assertEqual(
            stamp.common_date.ordinal,
            260,
        )
        self.assertEqual(
            (
                stamp.common_date.month,
                stamp.common_date.day,
            ),
            (9, 18),
        )
        self.assertEqual(
            stamp.common_date.quarter,
            3,
        )
        self.assertEqual(
            stamp.common_date.week,
            38,
        )
        self.assertEqual(
            stamp.common_date.weekday,
            "Friday",
        )
        self.assertIsNone(
            stamp.reconciliation_address
        )
        self.assertEqual(
            stamp.civil_timestamp
            .utcoffset()
            .total_seconds(),
            -6 * 3600,
        )
        self.assertEqual(
            stamp.common_standard_timestamp
            .utcoffset()
            .total_seconds(),
            -7 * 3600,
        )

    def test_day_364_boundary_is_last_ordinary_address(self):
        opening = date(2026, 1, 1)
        stamp = self._stamp(
            instant=self._after_boundary(
                opening + timedelta(days=363)
            ),
            opening=opening,
        )
        self.assertEqual(
            stamp.state,
            "ORDINARY",
        )
        self.assertEqual(
            stamp.common_date.ordinal,
            364,
        )
        self.assertEqual(
            stamp.calendar_address,
            "Y_2026-364",
        )
        self.assertEqual(
            stamp.continuous_k,
            363,
        )

    def test_every_reconciliation_day_has_only_r_address(self):
        opening = date(2026, 1, 1)

        for r_day in range(1, 8):
            stamp = self._stamp(
                instant=self._after_boundary(
                    opening
                    + timedelta(
                        days=363 + r_day
                    )
                ),
                opening=opening,
            )
            self.assertEqual(
                stamp.state,
                "RECONCILIATION",
            )
            self.assertEqual(
                stamp.reconciliation_day,
                r_day,
            )
            self.assertEqual(
                stamp.calendar_address,
                f"Y_2026/Y_2027-R{r_day}",
            )
            self.assertEqual(
                stamp.reconciliation_address,
                stamp.calendar_address,
            )
            self.assertIsNone(
                stamp.common_date,
            )
            self.assertEqual(
                stamp.continuous_k,
                363 + r_day,
            )

            snapshot = get_calendar_snapshot(
                stamp.instant_utc,
                config=CalendarConfig(
                    location=self.point,
                    local_zone="America/Denver",
                    common_year=2026,
                    opening_civil_date=opening,
                    day001_weekday="Friday",
                    reconciliation_days_after_completion=7,
                    common_standard_offset_seconds=-7 * 3600,
                    continuous_k_at_opening=0,
                ),
            )
            self.assertIsNone(
                snapshot.common_date,
            )
            self.assertIsNone(
                snapshot.annual_phase,
            )
            self.assertIsNone(
                snapshot.solar_gate,
            )
            self.assertEqual(
                snapshot.calendar_address,
                f"Y_2026/Y_2027-R{r_day}",
            )

    def test_next_day001_reuses_same_continuous_k(self):
        opening = date(2026, 1, 1)
        next_opening = (
            opening + timedelta(days=371)
        )
        instant = self._after_boundary(
            next_opening
        )

        old_publication = self._stamp(
            instant=instant,
            opening=opening,
            common_year=2026,
            reconciliation=7,
            continuous_k=0,
        )
        new_publication = self._stamp(
            instant=instant,
            opening=next_opening,
            common_year=2027,
            reconciliation=0,
            continuous_k=371,
        )

        self.assertEqual(
            old_publication.state,
            "OUTSIDE_RANGE",
        )
        self.assertIsNone(
            old_publication.calendar_address,
        )
        self.assertEqual(
            old_publication.continuous_k,
            371,
        )

        self.assertEqual(
            new_publication.state,
            "ORDINARY",
        )
        self.assertEqual(
            new_publication.calendar_address,
            "Y_2027-001",
        )
        self.assertEqual(
            new_publication.common_date.ordinal,
            1,
        )
        self.assertEqual(
            new_publication.continuous_k,
            371,
        )
        self.assertEqual(
            new_publication.common_date.weekday,
            "Friday",
        )

    def test_no_reconciliation_path_goes_negative_or_breaks_week_span(self):
        opening = date(2026, 1, 1)
        seen_k = []

        for offset in range(364 + 7 + 1):
            stamp = self._stamp(
                instant=self._after_boundary(
                    opening + timedelta(days=offset)
                ),
                opening=opening,
            )
            seen_k.append(
                stamp.continuous_k
            )

        self.assertEqual(
            seen_k,
            list(range(372)),
        )

    def test_before_k_epoch_has_no_continuous_k_or_address(self):
        opening = date(2026, 1, 1)
        stamp = self._stamp(
            instant=self._after_boundary(
                opening - timedelta(days=1)
            ),
            opening=opening,
            continuous_k=0,
        )
        self.assertEqual(
            stamp.state,
            "OUTSIDE_RANGE",
        )
        self.assertIsNone(
            stamp.continuous_k,
        )
        self.assertIsNone(
            stamp.calendar_address,
        )

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
