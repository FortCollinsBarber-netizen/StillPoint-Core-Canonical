from __future__ import annotations

from datetime import date, timedelta

from .models import CommonDate

# Ratified immutable Common Calendar surface:
# familiar non-leap civil month lengths, except December ends on Day 30.
# 365 - December 31 = 364 = 52 * 7.
MONTH_LENGTHS = (
    31, 28, 31,
    30, 31, 30,
    31, 31, 30,
    31, 30, 30,
)
QUARTER_LENGTHS = tuple(
    sum(MONTH_LENGTHS[index:index + 3])
    for index in range(0, 12, 3)
)
WEEKDAYS = (
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
)


def validate_grid() -> None:
    if sum(MONTH_LENGTHS) != 364:
        raise RuntimeError(
            "Common year must total exactly 364 days"
        )
    if 364 % 7 != 0:
        raise RuntimeError(
            "Common year must contain complete seven-day weeks"
        )
    if MONTH_LENGTHS[1] != 28:
        raise RuntimeError(
            "February 29 does not exist in the Common Calendar"
        )
    if MONTH_LENGTHS[11] != 30:
        raise RuntimeError(
            "December 31 does not exist in the Common Calendar"
        )


def ordinal_day(month: int, day: int) -> int:
    validate_grid()
    if not 1 <= month <= 12:
        raise ValueError("month must be within 1..12")
    length = MONTH_LENGTHS[month - 1]
    if not 1 <= day <= length:
        raise ValueError(
            f"day must be within 1..{length} for month {month}"
        )
    return sum(MONTH_LENGTHS[:month - 1]) + day


def month_day_from_ordinal(
    ordinal: int,
) -> tuple[int, int]:
    validate_grid()
    if not 1 <= ordinal <= 364:
        raise ValueError(
            "ordinal must be within 1..364"
        )
    remaining = ordinal
    for month, length in enumerate(
        MONTH_LENGTHS,
        start=1,
    ):
        if remaining <= length:
            return month, remaining
        remaining -= length
    raise AssertionError("unreachable")


def weekday_for_ordinal(
    ordinal: int,
    day001_weekday: str,
) -> str:
    if day001_weekday not in WEEKDAYS:
        raise ValueError(
            f"unknown weekday epoch: {day001_weekday}"
        )
    start = WEEKDAYS.index(day001_weekday)
    return WEEKDAYS[
        (start + ordinal - 1) % 7
    ]


def common_date(
    *,
    year: int,
    ordinal: int,
    day001_weekday: str,
) -> CommonDate:
    month, day = month_day_from_ordinal(
        ordinal
    )
    quarter = ((month - 1) // 3) + 1
    quarter_start_ordinal = (
        sum(
            QUARTER_LENGTHS[
                :quarter - 1
            ]
        )
        + 1
    )
    return CommonDate(
        year=year,
        ordinal=ordinal,
        month=month,
        day=day,
        quarter=quarter,
        day_of_quarter=(
            ordinal
            - quarter_start_ordinal
            + 1
        ),
        week=((ordinal - 1) // 7) + 1,
        day_in_week=((ordinal - 1) % 7) + 1,
        weekday=weekday_for_ordinal(
            ordinal,
            day001_weekday,
        ),
    )


def boundary_dates_for_common_date(
    *,
    opening_civil_date: date,
    month: int,
    day: int,
) -> tuple[date, date]:
    ordinal = ordinal_day(month, day)
    opens_on = (
        opening_civil_date
        + timedelta(days=ordinal - 1)
    )
    return (
        opens_on,
        opens_on + timedelta(days=1),
    )
