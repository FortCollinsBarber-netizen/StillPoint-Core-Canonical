from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .models import GeoPoint
from .service import CalendarConfig, get_calendar_snapshot
from .spec import SPEC_VERSION
from .sunset import apparent_sunrise_utc, apparent_sunset_utc

UTC = timezone.utc
VECTORS_VERSION = "stillpoint-calendar-projection-vectors-v1"

# Public conformance point only. It is not Ground Zero and has no civic authority.
CONFORMANCE_POINT = GeoPoint(40.3978, -105.0749, "LOVELAND_TEST")
CONFORMANCE_ZONE = "America/Denver"


def _iso_seconds(value: datetime) -> str:
    value = value.astimezone(UTC).replace(microsecond=0)
    return value.isoformat().replace("+00:00", "Z")


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
        "ordinaryAddress": snapshot.ordinary_address,
        "reconciliationAddress": snapshot.reconciliation_address,
        "reconciliationDay": snapshot.reconciliation_day,
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
        "namedDay": snapshot.named_day,
        "sabbath": snapshot.sabbath_active,
        "lordsDay": snapshot.lords_day_active,
        "stillPoint": snapshot.stillpoint_active,
        "annualPhase": snapshot.annual_phase,
        "solarGate": snapshot.solar_gate,
        "civilOffsetSeconds": _offset_seconds(snapshot.civil_timestamp),
        "commonStandardOffsetSeconds": _offset_seconds(
            snapshot.common_standard_timestamp
        ),
        "nextProtectedBoundaryLabel": snapshot.next_protected_boundary_label,
    }


def _vector(
    vector_id: str,
    instant: datetime,
    config: CalendarConfig,
    *,
    kind: str = "positive",
) -> dict[str, Any]:
    snapshot = get_calendar_snapshot(instant, config=config)
    return {
        "id": vector_id,
        "kind": kind,
        "instantUTC": _iso_seconds(instant),
        "expected": _expected(snapshot),
    }


def build_calendar_projection_vectors() -> dict[str, Any]:
    ordinary = CalendarConfig(
        location=CONFORMANCE_POINT,
        local_zone=CONFORMANCE_ZONE,
        common_year=2026,
        opening_civil_date=date(2026, 1, 1),
        day001_weekday="Friday",
        common_standard_offset_seconds=-7 * 3600,
        opening_continuous_k=0,
    )
    with_reconciliation = CalendarConfig(
        location=CONFORMANCE_POINT,
        local_zone=CONFORMANCE_ZONE,
        common_year=2026,
        opening_civil_date=date(2026, 1, 1),
        day001_weekday="Friday",
        common_standard_offset_seconds=-7 * 3600,
        reconciliation_days_after_completion=7,
        opening_continuous_k=0,
    )

    friday_sunset = apparent_sunset_utc(date(2026, 9, 18), CONFORMANCE_POINT)
    saturday_sunset = apparent_sunset_utc(date(2026, 9, 19), CONFORMANCE_POINT)
    sunday_sunrise = apparent_sunrise_utc(date(2026, 9, 20), CONFORMANCE_POINT)
    sunday_sunset = apparent_sunset_utc(date(2026, 9, 20), CONFORMANCE_POINT)

    r3_boundary = apparent_sunset_utc(
        ordinary.opening_civil_date + timedelta(days=366),
        CONFORMANCE_POINT,
    )
    outside_boundary = apparent_sunset_utc(
        ordinary.opening_civil_date + timedelta(days=371),
        CONFORMANCE_POINT,
    )

    vectors = [
        _vector(
            "observation-zero",
            datetime(2026, 9, 18, 19, 28, 57, tzinfo=UTC),
            ordinary,
        ),
        _vector("friday-after-sunset", friday_sunset + timedelta(seconds=1), ordinary),
        _vector(
            "saturday-after-sunset",
            saturday_sunset + timedelta(seconds=1),
            ordinary,
        ),
        _vector(
            "sunday-before-sunrise",
            sunday_sunrise - timedelta(seconds=1),
            ordinary,
        ),
        _vector(
            "sunday-after-sunrise",
            sunday_sunrise + timedelta(seconds=1),
            ordinary,
        ),
        _vector("sunday-after-sunset", sunday_sunset + timedelta(seconds=1), ordinary),
        _vector(
            "reconciliation-r3",
            r3_boundary + timedelta(seconds=1),
            with_reconciliation,
            kind="negative-ordinary-address",
        ),
        _vector(
            "outside-publication-range",
            outside_boundary + timedelta(seconds=1),
            with_reconciliation,
            kind="fail-closed",
        ),
    ]

    return {
        "version": VECTORS_VERSION,
        "specVersion": SPEC_VERSION,
        "referenceStatus": "public-conformance-only-not-ground-zero",
        "conformanceContext": {
            "locationId": CONFORMANCE_POINT.id,
            "latitude": CONFORMANCE_POINT.latitude,
            "longitude": CONFORMANCE_POINT.longitude,
            "legalCivilZone": CONFORMANCE_ZONE,
            "commonYear": 2026,
            "openingCivilDate": "2026-01-01",
            "day001Weekday": "Friday",
            "commonStandardOffsetSeconds": -7 * 3600,
            "openingContinuousK": 0,
        },
        "vectors": vectors,
    }


def export_calendar_projection_vectors(path: Path) -> None:
    path.write_text(
        json.dumps(build_calendar_projection_vectors(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
