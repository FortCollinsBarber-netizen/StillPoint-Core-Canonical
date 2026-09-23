from __future__ import annotations

from datetime import datetime, timezone

from stillpoint.calendar_core.lunar import lunar_phase_state
from stillpoint.calendar_core.runtime_surface import clock_snapshot_payload


def test_ground_zero_epoch_observation_projects_full_clock_snapshot():
    instant = datetime(2026, 9, 23, 11, 32, 9, tzinfo=timezone.utc)
    value = clock_snapshot_payload(
        instant,
        latitude=40.3978,
        longitude=-105.0749,
        local_zone="America/Denver",
    )

    assert value["schema"] == "stillpoint.clock-snapshot.v1"
    assert value["authority"] == "read-only-clock-projection"
    assert value["location"]["coordinate_system"] == "WGS84"
    assert value["calendar"]["calendar_address"] == "Y_2026-265"
    assert value["calendar"]["map"]["year_days"] == 364
    assert value["calendar"]["map"]["weeks_per_year"] == 52
    assert value["solar_boundaries"]["previous_boundary_civil_date"] == "2026-09-22"
    assert value["protected_time"]["named_day"] == "Wednesday"
    assert value["lunar"]["phase"] == "WAXING GIBBOUS"
    assert value["lunar"]["waxing"] is True
    assert 85 <= value["lunar"]["illumination_percent"] <= 95


def test_lunar_witness_tracks_usno_primary_phase_times():
    new_moon = lunar_phase_state(
        datetime(2026, 9, 11, 3, 27, tzinfo=timezone.utc)
    )
    full_moon = lunar_phase_state(
        datetime(2026, 9, 26, 16, 49, tzinfo=timezone.utc)
    )

    assert new_moon.phase_name == "NEW MOON"
    assert new_moon.illumination_fraction < 0.02
    assert full_moon.phase_name == "FULL MOON"
    assert full_moon.illumination_fraction > 0.99
