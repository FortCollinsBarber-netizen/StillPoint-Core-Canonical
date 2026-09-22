from __future__ import annotations

from datetime import date, timedelta

from .models import CommonDate

# Ratified Common Calendar month surface.
#
# The month labels intentionally follow the 2026 common-year pattern, with
# December capped at 30.  December 31 is not a Common Calendar date.
# 31+28+31+30+31+30+31+31+30+31+30+30 = 364 = 52 * 7.
MONTH_LENGTHS = (
    31, 28, 31, 30, 31, 30,
    31, 31, 30, 31, 30, 30,
)
BASE_YEAR_DAYS = 364
WEEK_DAYS = 7
SEASON_DAYS = 91
SEASON_COUNT = 4

WEEKDAYS = (
    "Sunday", "Monday", "Tuesday", "Wednesday",
    "Thursday", "Friday", "Saturday",
)


def validate_grid() -> None:
    if sum(MONTH_LENGTHS) != BASE_YEAR_DAYS:
        raise RuntimeError("Common year must total exactly 364 days")
    if BASE_YEAR_DAYS % WEEK_DAYS != 0:
        raise RuntimeError("Common year must contain an exact number of weeks")
    if SEASON_DAYS * SEASON_COUNT != BASE_YEAR_DAYS:
        raise RuntimeError("four Enochic seasons must total 364 days")
    if MONTH_LENGTHS[-1] != 30:
        raise RuntimeError("December 31 must not exist in Common Calendar law")


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
    if not 1 <= ordinal <= BASE_YEAR_DAYS:
        raise ValueError("ordinal must be within 1..364")
    remaining = ordinal
    for month, length in enumerate(MONTH_LENGTHS, start=1):
        if remaining <= length:
            return month, remaining
        remaining -= length
    raise AssertionError("unreachable")


def weekday_for_ordinal(ordinal: int, day001_weekday: str) -> str:
    if day001_weekday not in WEEKDAYS:
        raise ValueError(f"unknown weekday epoch: {day001_weekday}")
    start = WEEKDAYS.index(day001_weekday)
    return WEEKDAYS[(start + ordinal - 1) % WEEK_DAYS]


def common_date(*, year: int, ordinal: int, day001_weekday: str) -> CommonDate:
    month, day = month_day_from_ordinal(ordinal)
    return CommonDate(
        year=year,
        ordinal=ordinal,
        month=month,
        day=day,
        # Season/quarter geometry is a 91-day ordinal layer. It is deliberately
        # independent of the familiar month labels above.
        quarter=((ordinal - 1) // SEASON_DAYS) + 1,
        day_of_quarter=((ordinal - 1) % SEASON_DAYS) + 1,
        week=((ordinal - 1) // WEEK_DAYS) + 1,
        day_in_week=((ordinal - 1) % WEEK_DAYS) + 1,
        weekday=weekday_for_ordinal(ordinal, day001_weekday),
    )


def boundary_dates_for_common_date(
    *,
    opening_civil_date: date,
    month: int,
    day: int,
) -> tuple[date, date]:
    ordinal = ordinal_day(month, day)
    opens_on = opening_civil_date + timedelta(days=ordinal - 1)
    return opens_on, opens_on + timedelta(days=1)
