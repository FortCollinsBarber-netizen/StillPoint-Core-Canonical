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
        self.assertFalse(snapshot["invariants"]["astronomy_mutates_grid"])

    def test_clock_os_is_outside_range_before_first_enacted_sunset(self):
        before = (
            apparent_sunset_utc(date(2026, 1, 1), TEST_LOCATION)
            - timedelta(minutes=30)
        )
        snapshot = clock_snapshot(before, config=CONFIG)

        self.assertEqual(snapshot["calendar_state"], "OUTSIDE_RANGE")
        self.assertIsNone(snapshot["calendar"])
        self.assertIsNone(address_for_instant(before, config=CONFIG))

    def test_clock_os_rolls_day_364_directly_to_next_year_day_001(self):
        final_day_2026 = _after_sunset(date(2026, 12, 30))
        end_snapshot = clock_snapshot(final_day_2026, config=CONFIG)

        self.assertEqual(
            end_snapshot["calendar"]["calendar_address"],
            "Y_2026-364",
        )
        self.assertEqual(
            end_snapshot["boundaries"]["next_begins"]["calendar_address"],
            "Y_2027-001",
        )

        first_2027 = _after_sunset(date(2026, 12, 31))
        next_snapshot = clock_snapshot(first_2027, config=CONFIG)
        self.assertEqual(
            next_snapshot["calendar"]["calendar_address"],
            "Y_2027-001",
        )
        self.assertEqual(
            next_snapshot["calendar"]["common_date"]["weekday"],
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
