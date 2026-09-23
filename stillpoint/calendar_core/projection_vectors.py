from __future__ import annotations

import json
from datetime import (
    date,
    datetime,
    timedelta,
    timezone,
)
from pathlib import Path
from typing import Any

from .contract import (
    CONFORMANCE_POINT,
    CONFORMANCE_ZONE,
)
from .service import (
    CalendarConfig,
    get_calendar_snapshot,
)
from .sunset import (
    apparent_sunrise_utc,
    apparent_sunset_utc,
)

UTC = timezone.utc
PROJECTION_VECTOR_VERSION = (
    "stillpoint-calendar-projection-vectors-v2"
)


def _iso_seconds(
    value: datetime,
) -> str:
    return (
        value.astimezone(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _offset_seconds(
    value: datetime,
) -> int:
    offset = value.utcoffset()
    if offset is None:
        raise ValueError(
            "datetime has no UTC offset"
        )
    return int(
        offset.total_seconds()
    )


def _expected(
    snapshot,
) -> dict[str, Any]:
    common = snapshot.common_date
    return {
        "continuousK":
            snapshot.continuous_k,
        "state":
            snapshot.state,
        "calendarAddress":
            snapshot.calendar_address,
        "commonDate":
            None
            if common is None
            else {
                "year":
                    common.year,
                "ordinal":
                    common.ordinal,
                "month":
                    common.month,
                "day":
                    common.day,
                "quarter":
                    common.quarter,
                "dayOfQuarter":
                    common.day_of_quarter,
                "week":
                    common.week,
                "dayInWeek":
                    common.day_in_week,
                "weekday":
                    common.weekday,
            },
        "namedDay":
            snapshot.named_day,
        "sabbath":
            snapshot.sabbath_active,
        "lordsDay":
            snapshot.lords_day_active,
        "stillPoint":
            snapshot.stillpoint_active,
        "annualPhase":
            snapshot.annual_phase,
        "solarGate":
            snapshot.solar_gate,
        "civilOffsetSeconds":
            _offset_seconds(
                snapshot.civil_timestamp
            ),
        "commonStandardOffsetSeconds":
            _offset_seconds(
                snapshot.common_standard_timestamp
            ),
        "nextProtectedBoundaryLabel":
            snapshot.next_protected_boundary_label,
    }


def _config(
    *,
    common_year: int = 1,
    opening: date = date(
        2026,
        1,
        1,
    ),
    continuous_k: int = 0,
) -> CalendarConfig:
    return CalendarConfig(
        location=CONFORMANCE_POINT,
        local_zone=CONFORMANCE_ZONE,
        common_year=common_year,
        opening_civil_date=opening,
        day001_weekday="Thursday",
        common_standard_offset_seconds=
            -7 * 3600,
        continuous_k_at_opening=
            continuous_k,
        reference_rule_version=
            "immutable-364-v1",
        reference_station_id=None,
        ephemeris_id=None,
    )


def _vector(
    vector_id: str,
    instant: datetime,
    *,
    config: CalendarConfig | None = None,
) -> dict[str, Any]:
    if config is None:
        config = _config()
    return {
        "id": vector_id,
        "instantUTC":
            _iso_seconds(instant),
        "expected":
            _expected(
                get_calendar_snapshot(
                    instant,
                    config=config,
                )
            ),
    }


def build_calendar_projection_vectors(
) -> dict[str, Any]:
    friday_sunset = (
        apparent_sunset_utc(
            date(2026, 9, 18),
            CONFORMANCE_POINT,
        )
    )
    saturday_sunset = (
        apparent_sunset_utc(
            date(2026, 9, 19),
            CONFORMANCE_POINT,
        )
    )
    sunday_sunrise = (
        apparent_sunrise_utc(
            date(2026, 9, 20),
            CONFORMANCE_POINT,
        )
    )
    sunday_sunset = (
        apparent_sunset_utc(
            date(2026, 9, 20),
            CONFORMANCE_POINT,
        )
    )
    day364_sunset = (
        apparent_sunset_utc(
            date(2026, 12, 30),
            CONFORMANCE_POINT,
        )
    )
    next_opening = date(
        2026,
        12,
        31,
    )
    next_year_sunset = (
        apparent_sunset_utc(
            next_opening,
            CONFORMANCE_POINT,
        )
    )

    return {
        "version":
            PROJECTION_VECTOR_VERSION,
        "authorityStatus":
            "conformance-only",
        "fixture": {
            "locationId":
                CONFORMANCE_POINT.id,
            "latitude":
                CONFORMANCE_POINT.latitude,
            "longitude":
                CONFORMANCE_POINT.longitude,
            "legalCivilZone":
                CONFORMANCE_ZONE,
            "commonYear": 1,
            "openingCivilDate":
                "2026-01-01",
            "day001Weekday":
                "Thursday",
            "commonStandardOffsetSeconds":
                -7 * 3600,
            "continuousKAtOpening": 0,
            "baseYearDays": 364,
            "weeksPerYear": 52,
        },
        "vectors": [
            _vector(
                "observation-zero",
                datetime(
                    2026,
                    9,
                    18,
                    19,
                    28,
                    57,
                    tzinfo=UTC,
                ),
            ),
            _vector(
                "friday-after-sunset",
                friday_sunset
                + timedelta(seconds=1),
            ),
            _vector(
                "saturday-after-sunset",
                saturday_sunset
                + timedelta(seconds=1),
            ),
            _vector(
                "sunday-before-sunrise",
                sunday_sunrise
                - timedelta(seconds=1),
            ),
            _vector(
                "sunday-after-sunrise",
                sunday_sunrise
                + timedelta(seconds=1),
            ),
            _vector(
                "sunday-after-sunset",
                sunday_sunset
                + timedelta(seconds=1),
            ),
            _vector(
                "day-364-december-30",
                day364_sunset
                + timedelta(seconds=1),
            ),
            _vector(
                "next-year-day-001",
                next_year_sunset
                + timedelta(seconds=1),
                config=_config(
                    common_year=2,
                    opening=next_opening,
                    continuous_k=364,
                ),
            ),
        ],
        "failureCases": [
            {
                "id":
                    "r-address-rejected",
                "kind":
                    "address",
                "input": {
                    "address":
                        "Y_1/Y_2-R1",
                },
                "expectedFailure":
                    "INVALID_CALENDAR_ADDRESS",
            },
            {
                "id":
                    "december-31-rejected",
                "kind":
                    "common-date",
                "input": {
                    "month": 12,
                    "day": 31,
                },
                "expectedFailure":
                    "INVALID_MONTH_DAY",
            },
            {
                "id":
                    "february-29-rejected",
                "kind":
                    "common-date",
                "input": {
                    "month": 2,
                    "day": 29,
                },
                "expectedFailure":
                    "INVALID_MONTH_DAY",
            },
            {
                "id":
                    "unsupported-spec-version",
                "kind":
                    "spec",
                "input": {
                    "version":
                        "unsupported-calendar-spec",
                },
                "expectedFailure":
                    "UNSUPPORTED_SPEC_VERSION",
            },
        ],
    }


def export_calendar_projection_vectors(
    path: Path,
) -> None:
    path.write_text(
        json.dumps(
            build_calendar_projection_vectors(),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
