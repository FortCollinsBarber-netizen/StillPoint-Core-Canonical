from __future__ import annotations

from datetime import date, timedelta

from .models import CommonDate

MONTH_LENGTHS = (30, 30, 31) * 4
WEEKDAYS = (
    "Sunday", "Monday", "Tuesday", "Wednesday",
    "Thursday", "Friday", "Saturday",
)


def validate_grid() -> None:
    if sum(MONTH_LENGTHS) != 364:
        raise RuntimeError("ordinary Common year must total 364 days")
    for quarter in range(0, 12, 3):
        if sum(MONTH_LENGTHS[quarter:quarter + 3]) != 91:
            raise RuntimeError("every Common quarter must total 91 days")


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


def weekday_for_ordinal(ordinal: int, day001_weekday: str) -> str:
    if day001_weekday not in WEEKDAYS:
        raise ValueError(f"unknown weekday epoch: {day001_weekday}")
    start = WEEKDAYS.index(day001_weekday)
    return WEEKDAYS[(start + ordinal - 1) % 7]


def common_date(*, year: int, ordinal: int, day001_weekday: str) -> CommonDate:
    month, day = month_day_from_ordinal(ordinal)
    return CommonDate(
        year=year,
        ordinal=ordinal,
        month=month,
        day=day,
        quarter=((ordinal - 1) // 91) + 1,
        day_of_quarter=((ordinal - 1) % 91) + 1,
        week=((ordinal - 1) // 7) + 1,
        day_in_week=((ordinal - 1) % 7) + 1,
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
