from __future__ import annotations

from datetime import date, timedelta

from .models import CommonDate

MONTH_NAMES = (
    "January", "February", "March", "April",
    "May", "June", "July", "August",
    "September", "October", "November", "December",
)
MONTH_LENGTHS = (
    31, 28, 31,
    30, 31, 30,
    31, 31, 30,
    31, 30, 30,
)
CANONICAL_TEMPLATE_YEAR = 2026
QUARTER_DAYS = 91
QUARTERS = 4
WEEKDAYS = (
    "Sunday", "Monday", "Tuesday", "Wednesday",
    "Thursday", "Friday", "Saturday",
)
CANONICAL_DAY001_WEEKDAY = "Thursday"


def validate_grid() -> None:
    if len(MONTH_NAMES) != 12 or len(MONTH_LENGTHS) != 12:
        raise RuntimeError("Common Calendar must preserve twelve familiar months")
    if sum(MONTH_LENGTHS) != 364:
        raise RuntimeError("Common year must total exactly 364 days")
    if 364 % 7 != 0:
        raise RuntimeError("Common year must contain complete seven-day weeks")
    if QUARTER_DAYS * QUARTERS != 364:
        raise RuntimeError("seasonal quarters must total exactly 364 days")
    if MONTH_LENGTHS[1] != 28:
        raise RuntimeError("February 29 does not exist in the Common Calendar")
    if MONTH_LENGTHS[11] != 30:
        raise RuntimeError("December 31 does not exist in the Common Calendar")


def ordinal_day(month: int, day: int) -> int:
    validate_grid()
    if not 1 <= month <= 12:
        raise ValueError("month must be within 1..12")
    length = MONTH_LENGTHS[month - 1]
    if not 1 <= day <= length:
        raise ValueError(f"day must be within 1..{length} for month {month}")
    return sum(MONTH_LENGTHS[:month - 1]) + day


def month_day_from_ordinal(ordinal: int) -> tuple[int, int]:
    validate_grid()
    if not 1 <= ordinal <= 364:
        raise ValueError("ordinal must be within 1..364")
    remaining = ordinal
    for month, length in enumerate(MONTH_LENGTHS, start=1):
        if remaining <= length:
            return month, remaining
        remaining -= length
    raise AssertionError("unreachable")


def weekday_for_ordinal(ordinal: int) -> str:
    if not 1 <= ordinal <= 364:
        raise ValueError("ordinal must be within 1..364")
    start = WEEKDAYS.index(CANONICAL_DAY001_WEEKDAY)
    return WEEKDAYS[(start + ordinal - 1) % 7]


def common_date(*, year: int, ordinal: int) -> CommonDate:
    month, day = month_day_from_ordinal(ordinal)
    return CommonDate(
        year=year,
        ordinal=ordinal,
        month=month,
        day=day,
        quarter=((ordinal - 1) // QUARTER_DAYS) + 1,
        day_of_quarter=((ordinal - 1) % QUARTER_DAYS) + 1,
        week=((ordinal - 1) // 7) + 1,
        day_in_week=((ordinal - 1) % 7) + 1,
        weekday=weekday_for_ordinal(ordinal),
    )


def boundary_dates_for_common_date(
    *, opening_civil_date: date, month: int, day: int
) -> tuple[date, date]:
    ordinal = ordinal_day(month, day)
    opens_on = opening_civil_date + timedelta(days=ordinal - 1)
    return opens_on, opens_on + timedelta(days=1)
