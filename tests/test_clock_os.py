from __future__ import annotations

from contextlib import redirect_stdout
from datetime import date, datetime, timedelta, timezone
from io import StringIO
import os
from pathlib import Path
import tempfile
import unittest

from stillpoint.cli import main as cli_main
from stillpoint.clock_os import (
    CLOCK_SCHEMA,
    ClockConfig,
    address_for_instant,
    canonical_civil_window,
    clock_snapshot,
)
from stillpoint.calendar_core.models import GeoPoint
from stillpoint.calendar_core.sunset import apparent_sunset_utc
from stillpoint.lunar import (
    REFERENCE_NEW_MOON,
    SYNODIC_MONTH_DAYS,
    lunar_phase_witness,
)


TEST_LOCATION = GeoPoint(latitude=40.0, longitude=-105.0, id="CLOCK_TEST")
CONFIG = ClockConfig(
    location=TEST_LOCATION,
    local_zone="America/Denver",
    common_standard_offset_seconds=-7 * 3600,
)


def _after_sunset(day: date) -> datetime:
    return apparent_sunset_utc(day, TEST_LOCATION) + timedelta(minutes=30)


class ClockOSTests(unittest.TestCase):
    def test_clock_os_resolves_first_enacted_day_after_dusk(self):
        snapshot = clock_snapshot(_after_sunset(date(2026, 1, 1)), config=CONFIG)

        self.assertEqual(snapshot["schema"], CLOCK_SCHEMA)
        self.assertEqual(snapshot["authority"], "read-only-temporal-projection")
        self.assertEqual(snapshot["calendar_state"], "ORDINARY")
        self.assertEqual(snapshot["calendar"]["calendar_address"], "Y_2026-001")
        self.assertEqual(snapshot["calendar"]["common_date"]["weekday"], "Thursday")
        self.assertEqual(snapshot["calendar"]["map"]["year_count"], 50)
        self.assertEqual(snapshot["calendar"]["map"]["total_days"], 18_200)
        self.assertEqual(snapshot["location"]["coordinate_system"], "WGS84")
        self.assertEqual(snapshot["location"]["latitude"], TEST_LOCATION.latitude)
        self.assertEqual(snapshot["location"]["longitude"], TEST_LOCATION.longitude)
        self.assertFalse(snapshot["invariants"]["astronomy_mutates_grid"])
        self.assertFalse(snapshot["invariants"]["lunar_witness_mutates_grid"])
        self.assertEqual(
            snapshot["lunar_witness"]["calendar_effect"],
            "none",
        )

    def test_clock_os_is_outside_range_before_first_enacted_midnight(self):
        common_zone = timezone(timedelta(hours=-7))
        before = datetime(
            2025, 12, 31, 23, 59, 59, tzinfo=common_zone
        )
        snapshot = clock_snapshot(before, config=CONFIG)

        self.assertEqual(snapshot["calendar_state"], "OUTSIDE_RANGE")
        self.assertIsNone(snapshot["calendar"])
        self.assertIsNone(address_for_instant(before, config=CONFIG))

    def test_clock_os_rolls_day_364_directly_to_next_year_day_001_at_midnight(self):
        common_zone = timezone(timedelta(hours=-7))
        final_second = datetime(
            2026, 12, 30, 23, 59, 59, tzinfo=common_zone
        )
        next_second = datetime(
            2026, 12, 31, 0, 0, 0, tzinfo=common_zone
        )

        end_snapshot = clock_snapshot(final_second, config=CONFIG)
        next_snapshot = clock_snapshot(next_second, config=CONFIG)

        self.assertEqual(
            end_snapshot["calendar"]["calendar_address"],
            "Y_2026-364",
        )
        self.assertEqual(
            end_snapshot["boundaries"]["next_begins"]["calendar_address"],
            "Y_2027-001",
        )
        self.assertEqual(
            next_snapshot["calendar"]["calendar_address"],
            "Y_2027-001",
        )
        self.assertEqual(
            next_snapshot["calendar"]["common_date"]["weekday"],
            "Thursday",
        )
        self.assertEqual(
            next_snapshot["boundaries"]["calendar_date_boundary"],
            "common-standard-midnight",
        )
        self.assertEqual(
            end_snapshot["instant"]["common_calendar"]["display"],
            "2026-12-30 23:59:59",
        )
        self.assertEqual(
            next_snapshot["instant"]["common_calendar"]["display"],
            "2027-01-01 00:00:00",
        )
        self.assertEqual(
            next_snapshot["instant"]["common_calendar"]["weekday"],
            "Thursday",
        )

    def test_common_clock_uses_fixed_standard_offset_during_dst(self):
        instant = datetime(2026, 7, 15, 18, 0, tzinfo=timezone.utc)
        snapshot = clock_snapshot(instant, config=CONFIG)

        common = datetime.fromisoformat(snapshot["instant"]["common_standard"])
        civil = datetime.fromisoformat(snapshot["instant"]["civil"])
        self.assertEqual(common.utcoffset(), timedelta(hours=-7))
        self.assertEqual(civil.utcoffset(), timedelta(hours=-6))
        self.assertEqual(snapshot["instant"]["common_clock"], "11:00:00")


    def test_sunset_does_not_rename_the_calendar_date(self):
        common_zone = timezone(timedelta(hours=-7))
        before_sunset = datetime(2026, 1, 1, 12, 0, tzinfo=common_zone)
        after_sunset = datetime(2026, 1, 1, 20, 0, tzinfo=common_zone)

        before = clock_snapshot(before_sunset, config=CONFIG)
        after = clock_snapshot(after_sunset, config=CONFIG)

        self.assertEqual(before["calendar"]["calendar_address"], "Y_2026-001")
        self.assertEqual(after["calendar"]["calendar_address"], "Y_2026-001")
        self.assertFalse(
            before["invariants"]["solar_boundary_mutates_calendar_date"]
        )
        self.assertFalse(
            after["invariants"]["solar_boundary_mutates_calendar_date"]
        )

    def test_dst_civil_label_cannot_shift_common_calendar_date(self):
        # 00:30 daylight time is still 23:30 on the fixed Common Clock.
        instant = datetime(2026, 7, 15, 6, 30, tzinfo=timezone.utc)
        snapshot = clock_snapshot(instant, config=CONFIG)

        self.assertTrue(snapshot["instant"]["civil"].startswith("2026-07-15T00:30"))
        self.assertTrue(
            snapshot["instant"]["common_standard"].startswith("2026-07-14T23:30")
        )
        self.assertEqual(
            snapshot["boundaries"]["coordination_date"],
            "2026-07-14",
        )
        self.assertFalse(
            snapshot["invariants"]["daylight_saving_mutates_common_clock"]
        )

    def test_canonical_address_projects_to_location_specific_sunset_window(self):
        window = canonical_civil_window(2026, 1, config=CONFIG)

        self.assertEqual(window["calendar_address"], "Y_2026-001")
        self.assertEqual(window["opening_civil_date"], "2026-01-01")
        self.assertEqual(window["closing_civil_date"], "2026-01-02")
        self.assertGreater(
            datetime.fromisoformat(window["closes_at_utc"]),
            datetime.fromisoformat(window["opens_at_utc"]),
        )

    def test_naive_instant_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            clock_snapshot(datetime(2026, 1, 1, 12, 0), config=CONFIG)

    def test_clock_config_rejects_invalid_zone(self):
        with self.assertRaises(Exception):
            ClockConfig(
                location=TEST_LOCATION,
                local_zone="Not/A_Real_Zone",
                common_standard_offset_seconds=-7 * 3600,
            )

    def test_lunar_witness_matches_reference_and_phase_progression(self):
        reference = lunar_phase_witness(REFERENCE_NEW_MOON)
        self.assertAlmostEqual(reference["age_days"], 0.0, places=8)
        self.assertEqual(reference["phase_name"], "NEW MOON")
        self.assertTrue(reference["is_waxing"])
        self.assertEqual(reference["calendar_effect"], "none")

        first_quarter = lunar_phase_witness(
            REFERENCE_NEW_MOON
            + timedelta(days=SYNODIC_MONTH_DAYS / 4.0)
        )
        self.assertEqual(first_quarter["phase_name"], "FIRST QUARTER")
        self.assertTrue(first_quarter["is_waxing"])
        self.assertGreater(first_quarter["illumination_percent"], 45)
        self.assertLess(first_quarter["illumination_percent"], 55)

    def test_lunar_witness_tracks_september_2026_primary_phase_evidence(self):
        # USNO primary-phase evidence for September 2026:
        # New Moon 2026-09-11 03:27 UTC; Full Moon 2026-09-26 16:49 UTC.
        new_moon = lunar_phase_witness(
            datetime(2026, 9, 11, 3, 27, tzinfo=timezone.utc)
        )
        full_moon = lunar_phase_witness(
            datetime(2026, 9, 26, 16, 49, tzinfo=timezone.utc)
        )
        enactment = lunar_phase_witness(
            datetime(2026, 9, 23, 11, 32, 9, tzinfo=timezone.utc)
        )

        self.assertEqual(new_moon["phase_name"], "NEW MOON")
        self.assertLess(new_moon["illumination_fraction"], 0.02)
        self.assertEqual(full_moon["phase_name"], "FULL MOON")
        self.assertGreater(full_moon["illumination_fraction"], 0.99)
        self.assertEqual(enactment["phase_name"], "WAXING GIBBOUS")
        self.assertTrue(enactment["is_waxing"])
        self.assertGreater(enactment["illumination_percent"], 85)
        self.assertLess(enactment["illumination_percent"], 95)

    def test_lunar_state_cannot_change_calendar_address(self):
        instant = _after_sunset(date(2026, 1, 1))
        snapshot = clock_snapshot(instant, config=CONFIG)
        direct = address_for_instant(instant, config=CONFIG)

        self.assertEqual(direct, "Y_2026-001")
        self.assertEqual(snapshot["calendar"]["calendar_address"], direct)
        self.assertEqual(
            snapshot["lunar_witness"]["evidence_label"],
            "MEAN LUNATION · WITNESS ONLY",
        )

    def test_clock_cli_read_does_not_construct_company_state(self):
        instant = _after_sunset(date(2026, 1, 1))
        with tempfile.TemporaryDirectory() as td:
            old_cwd = os.getcwd()
            os.chdir(td)
            try:
                output = StringIO()
                with redirect_stdout(output):
                    rc = cli_main([
                        "clock-at",
                        "--instant", instant.isoformat(),
                        "--latitude", str(TEST_LOCATION.latitude),
                        "--longitude", str(TEST_LOCATION.longitude),
                        "--zone", CONFIG.local_zone,
                        "--standard-offset-seconds",
                        str(CONFIG.common_standard_offset_seconds),
                        "--location-id", TEST_LOCATION.id,
                    ])
                self.assertEqual(rc, 0)
                self.assertIn(
                    '"schema": "stillpoint.clock-os.v1"',
                    output.getvalue(),
                )
                self.assertFalse(
                    (Path(td) / "state" / "company.sqlite").exists()
                )
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()
