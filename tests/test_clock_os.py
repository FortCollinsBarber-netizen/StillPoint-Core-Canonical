from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

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


def test_clock_os_resolves_first_enacted_day_after_dusk():
    snapshot = clock_snapshot(_after_sunset(date(2026, 1, 1)), config=CONFIG)

    assert snapshot["schema"] == CLOCK_SCHEMA
    assert snapshot["authority"] == "read-only-temporal-projection"
    assert snapshot["calendar_state"] == "ORDINARY"
    assert snapshot["calendar"]["calendar_address"] == "Y_2026-001"
    assert snapshot["calendar"]["common_date"]["weekday"] == "Thursday"
    assert snapshot["calendar"]["map"]["year_count"] == 50
    assert snapshot["calendar"]["map"]["total_days"] == 18_200
    assert snapshot["invariants"]["astronomy_mutates_grid"] is False


def test_clock_os_is_outside_range_before_first_enacted_sunset():
    before = apparent_sunset_utc(date(2026, 1, 1), TEST_LOCATION) - timedelta(minutes=30)
    snapshot = clock_snapshot(before, config=CONFIG)

    assert snapshot["calendar_state"] == "OUTSIDE_RANGE"
    assert snapshot["calendar"] is None
    assert address_for_instant(before, config=CONFIG) is None


def test_clock_os_rolls_day_364_directly_to_next_year_day_001():
    final_day_2026 = _after_sunset(date(2026, 12, 30))
    end_snapshot = clock_snapshot(final_day_2026, config=CONFIG)

    assert end_snapshot["calendar"]["calendar_address"] == "Y_2026-364"
    assert end_snapshot["boundaries"]["next_begins"]["calendar_address"] == "Y_2027-001"

    first_2027 = _after_sunset(date(2026, 12, 31))
    next_snapshot = clock_snapshot(first_2027, config=CONFIG)
    assert next_snapshot["calendar"]["calendar_address"] == "Y_2027-001"
    assert next_snapshot["calendar"]["common_date"]["weekday"] == "Thursday"


def test_common_clock_uses_fixed_standard_offset_during_dst():
    instant = datetime(2026, 7, 15, 18, 0, tzinfo=timezone.utc)
    snapshot = clock_snapshot(instant, config=CONFIG)

    common = datetime.fromisoformat(snapshot["instant"]["common_standard"])
    civil = datetime.fromisoformat(snapshot["instant"]["civil"])
    assert common.utcoffset() == timedelta(hours=-7)
    assert civil.utcoffset() == timedelta(hours=-6)
    assert snapshot["instant"]["common_clock"] == "11:00:00"


def test_canonical_address_projects_to_location_specific_sunset_window():
    window = canonical_civil_window(2026, 1, config=CONFIG)

    assert window["calendar_address"] == "Y_2026-001"
    assert window["opening_civil_date"] == "2026-01-01"
    assert window["closing_civil_date"] == "2026-01-02"
    assert datetime.fromisoformat(window["closes_at_utc"]) > datetime.fromisoformat(
        window["opens_at_utc"]
    )


def test_naive_instant_fails_closed():
    with pytest.raises(ValueError, match="timezone-aware"):
        clock_snapshot(datetime(2026, 1, 1, 12, 0), config=CONFIG)


def test_clock_config_rejects_invalid_zone():
    with pytest.raises(Exception):
        ClockConfig(
            location=TEST_LOCATION,
            local_zone="Not/A_Real_Zone",
            common_standard_offset_seconds=-7 * 3600,
        )
