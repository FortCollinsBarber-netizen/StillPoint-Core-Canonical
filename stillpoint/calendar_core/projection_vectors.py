from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .contract import CONFORMANCE_POINT, CONFORMANCE_ZONE
from .service import CalendarConfig, get_calendar_snapshot
from .sunset import apparent_sunrise_utc, apparent_sunset_utc

UTC = timezone.utc
PROJECTION_VECTOR_VERSION = "stillpoint-calendar-projection-vectors-v2-fixed-364"


def _iso_seconds(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _offset_seconds(value: datetime) -> int:
    offset = value.utcoffset()
    if offset is None:
        raise ValueError("datetime has no UTC offset")
    return int(offset.total_seconds())


def _expected(snapshot) -> dict[str, Any]:
    common = snapshot.common_date
    return {
        "continuousK": snapshot.continuous_k,
        "state": snapshot.state,
        "commonDate": None if common is None else {
            "year": common.year,
            "ordinal": common.ordinal,
            "month": common.month,
            "day": common.day,
            "quarter": common.quarter,
            "week": common.week,
            "dayInWeek": common.day_in_week,
            "weekday": common.weekday,
        },
        "reconciliationDay": snapshot.reconciliation_day,
        "reconciliationAddress": snapshot.reconciliation_address,
        "namedDay": snapshot.named_day,
        "sabbath": snapshot.sabbath_active,
        "lordsDay": snapshot.lords_day_active,
        "stillPoint": snapshot.stillpoint_active,
        "annualPhase": snapshot.annual_phase,
        "solarGate": snapshot.solar_gate,
        "civilOffsetSeconds": _offset_seconds(snapshot.civil_timestamp),
        "commonStandardOffsetSeconds": _offset_seconds(snapshot.common_standard_timestamp),
        "nextProtectedBoundaryLabel": snapshot.next_protected_boundary_label,
    }


def _config() -> CalendarConfig:
    return CalendarConfig(
        location=CONFORMANCE_POINT,
        local_zone=CONFORMANCE_ZONE,
        common_year=2026,
        opening_civil_date=date(2026, 1, 1),
        day001_weekday="Thursday",
        common_standard_offset_seconds=-7 * 3600,
        reconciliation_days_after_completion=0,
        continuous_k_at_opening=0,
        reference_rule_version="fixed-364-v1",
        reference_station_id="LOVELAND_TEST",
        ephemeris_id="BOUNDARY_CONFORMANCE_ONLY",
    )


def _vector(vector_id: str, instant: datetime) -> dict[str, Any]:
    return {
        "id": vector_id,
        "instantUTC": _iso_seconds(instant),
        "reconciliationDaysAfterCompletion": 0,
        "expected": _expected(get_calendar_snapshot(instant, config=_config())),
    }


def build_calendar_projection_vectors() -> dict[str, Any]:
    friday_sunset = apparent_sunset_utc(date(2026, 9, 18), CONFORMANCE_POINT)
    saturday_sunset = apparent_sunset_utc(date(2026, 9, 19), CONFORMANCE_POINT)
    sunday_sunrise = apparent_sunrise_utc(date(2026, 9, 20), CONFORMANCE_POINT)
    sunday_sunset = apparent_sunset_utc(date(2026, 9, 20), CONFORMANCE_POINT)

    return {
        "version": PROJECTION_VECTOR_VERSION,
        "authorityStatus": "conformance-only",
        "fixture": {
            "locationId": CONFORMANCE_POINT.id,
            "latitude": CONFORMANCE_POINT.latitude,
            "longitude": CONFORMANCE_POINT.longitude,
            "legalCivilZone": CONFORMANCE_ZONE,
            "commonYear": 2026,
            "openingCivilDate": "2026-01-01",
            "day001Weekday": "Thursday",
            "commonStandardOffsetSeconds": -7 * 3600,
            "continuousKAtOpening": 0,
        },
        "vectors": [
            _vector("observation-zero", datetime(2026, 9, 18, 19, 28, 57, tzinfo=UTC)),
            _vector("friday-after-sunset", friday_sunset + timedelta(seconds=1)),
            _vector("saturday-after-sunset", saturday_sunset + timedelta(seconds=1)),
            _vector("sunday-before-sunrise", sunday_sunrise - timedelta(seconds=1)),
            _vector("sunday-after-sunrise", sunday_sunrise + timedelta(seconds=1)),
            _vector("sunday-after-sunset", sunday_sunset + timedelta(seconds=1)),
        ],
        "failureCases": [
            {
                "id": "any-reconciliation-is-invalid",
                "kind": "publication",
                "input": {"reconciliationDaysAfterCompletion": 7},
                "expectedFailure": "INVALID_RECONCILIATION",
            },
            {
                "id": "outside-publication-range",
                "kind": "projection",
                "instantUTC": "2028-01-01T12:00:00Z",
                "expectedFailure": "OUTSIDE_PUBLISHED_RANGE",
            },
            {
                "id": "unsupported-spec-version",
                "kind": "spec",
                "input": {"version": "unsupported-calendar-spec"},
                "expectedFailure": "UNSUPPORTED_SPEC_VERSION",
            },
        ],
    }


def export_calendar_projection_vectors(path: Path) -> None:
    path.write_text(
        json.dumps(build_calendar_projection_vectors(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
