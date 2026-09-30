from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .calendar import (
    CANONICAL_DAY001_WEEKDAY,
    MONTH_LENGTHS,
    QUARTER_DAYS,
)
from .gates import GATE_SEQUENCE, PHASE_LENGTHS
from .models import GeoPoint
from .service import CalendarConfig, get_calendar_snapshot
from .sunset import apparent_sunrise_utc, apparent_sunset_utc

UTC = timezone.utc
CONTRACT_VERSION = "stillpoint-calendar-core-contract-v2"

# Compatibility bridge only. These public test coordinates are not a national,
# civic, or constitutional reference point.
CONFORMANCE_POINT = GeoPoint(40.3978, -105.0749, "LOVELAND_TEST")
CONFORMANCE_ZONE = "America/Denver"


def _iso_seconds(value: datetime) -> str:
    return (
        value.astimezone(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _offset_seconds(value: datetime) -> int:
    offset = value.utcoffset()
    if offset is None:
        raise ValueError("datetime has no UTC offset")
    return int(offset.total_seconds())


def _expected(snapshot) -> dict[str, Any]:
    common = snapshot.common_date
    jubilee = snapshot.jubilee
    return {
        "continuousK": snapshot.continuous_k,
        "state": snapshot.state,
        "calendarAddress": snapshot.calendar_address,
        "commonDate": None if common is None else {
            "year": common.year,
            "ordinal": common.ordinal,
            "month": common.month,
            "day": common.day,
            "quarter": common.quarter,
            "dayOfQuarter": common.day_of_quarter,
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
        "jubilee": None if jubilee is None else {
            "cycle": jubilee.cycle,
            "cycleYear": jubilee.cycle_year,
            "sevenYearBlock": jubilee.seven_year_block,
            "yearWithinBlock": jubilee.year_within_block,
            "isSabbaticalThreshold": jubilee.is_sabbatical_threshold,
            "isJubileeYear": jubilee.is_jubilee_year,
        },
        "civilOffsetSeconds": _offset_seconds(snapshot.civil_timestamp),
        "commonStandardOffsetSeconds": _offset_seconds(
            snapshot.common_standard_timestamp
        ),
        "nextProtectedBoundaryLabel": snapshot.next_protected_boundary_label,
        "provenance": {
            "referenceRuleVersion": snapshot.reference_rule_version,
            "referenceStationId": snapshot.reference_station_id,
            "ephemerisId": snapshot.ephemeris_id,
        },
    }


def _vector(
    vector_id: str,
    instant: datetime,
    config: CalendarConfig,
) -> dict[str, Any]:
    return {
        "id": vector_id,
        "instantUTC": _iso_seconds(instant),
        "expected": _expected(
            get_calendar_snapshot(instant, config=config)
        ),
    }


def build_calendar_core_contract() -> dict[str, Any]:
    config = CalendarConfig(
        location=CONFORMANCE_POINT,
        local_zone=CONFORMANCE_ZONE,
        common_year=1,
        opening_civil_date=date(2026, 1, 1),
        common_standard_offset_seconds=-7 * 3600,
        reference_rule_version="immutable-364-v1",
        reference_station_id=None,
        ephemeris_id=None,
        jubilee_epoch_common_year=1,
        jubilee_epoch_cycle=1,
    )

    friday_sunset = apparent_sunset_utc(
        date(2026, 9, 18),
        CONFORMANCE_POINT,
    )
    saturday_sunset = apparent_sunset_utc(
        date(2026, 9, 19),
        CONFORMANCE_POINT,
    )
    sunday_sunrise = apparent_sunrise_utc(
        date(2026, 9, 20),
        CONFORMANCE_POINT,
    )
    sunday_sunset = apparent_sunset_utc(
        date(2026, 9, 20),
        CONFORMANCE_POINT,
    )

    vectors = [
        _vector(
            "observation-zero",
            datetime(2026, 9, 18, 19, 28, 57, tzinfo=UTC),
            config,
        ),
        _vector(
            "friday-after-sunset",
            friday_sunset + timedelta(seconds=1),
            config,
        ),
        _vector(
            "saturday-after-sunset",
            saturday_sunset + timedelta(seconds=1),
            config,
        ),
        _vector(
            "sunday-before-sunrise",
            sunday_sunrise - timedelta(seconds=1),
            config,
        ),
        _vector(
            "sunday-after-sunrise",
            sunday_sunrise + timedelta(seconds=1),
            config,
        ),
        _vector(
            "sunday-after-sunset",
            sunday_sunset + timedelta(seconds=1),
            config,
        ),
    ]

    return {
        "version": CONTRACT_VERSION,
        "jurisdiction": {
            "calendarNamespace": "stillpoint.calendar_core",
            "authorityNamespace": "stillpoint.temporal",
            "referenceStatus": "public-conformance-only-not-authority",
            "authorityStatus": "non-authoritative-compatibility-only",
        },
        "constants": {
            "apparentHorizonZenithDegrees": 90.8333,
            "baseYearDays": 364,
            "weekDays": 7,
            "weeksPerYear": 52,
            "day001Weekday": CANONICAL_DAY001_WEEKDAY,
            "monthLengths": list(MONTH_LENGTHS),
            "seasonalQuarterDays": QUARTER_DAYS,
            "phaseLengths": list(PHASE_LENGTHS),
            "gateSequence": list(GATE_SEQUENCE),
        },
        "conformanceContext": {
            "locationId": CONFORMANCE_POINT.id,
            "latitude": CONFORMANCE_POINT.latitude,
            "longitude": CONFORMANCE_POINT.longitude,
            "legalCivilZone": CONFORMANCE_ZONE,
            "commonYear": 1,
            "openingCivilDate": "2026-01-01",
            "day001Weekday": CANONICAL_DAY001_WEEKDAY,
            "commonStandardOffsetSeconds": -7 * 3600,
            "jubileeEpochCommonYear": 1,
            "jubileeEpochCycle": 1,
        },
        "goldenVectors": vectors,
    }


def export_calendar_core_contract(path: Path) -> None:
    path.write_text(
        json.dumps(
            build_calendar_core_contract(),
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
