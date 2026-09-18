#!/usr/bin/env python3
"""StillPoint fixed-grid, Jubilee, and Observation-Zero helpers."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

MONTH_LENGTHS = (30, 30, 31) * 4
WEEKDAYS = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")


def validate_grid() -> None:
    if sum(MONTH_LENGTHS) != 364:
        raise RuntimeError("ordinary year must contain exactly 364 days")
    if any(sum(MONTH_LENGTHS[q:q + 3]) != 91 for q in range(0, 12, 3)):
        raise RuntimeError("each quarter must contain exactly 91 days")


def ordinal_day(month: int, day: int) -> int:
    validate_grid()
    if not 1 <= month <= 12:
        raise ValueError("month must be 1..12")
    length = MONTH_LENGTHS[month - 1]
    if not 1 <= day <= length:
        raise ValueError(f"day must be 1..{length} for month {month}")
    return sum(MONTH_LENGTHS[:month - 1]) + day


def month_day_from_ordinal(ordinal: int) -> tuple[int, int]:
    validate_grid()
    if not 1 <= ordinal <= 364:
        raise ValueError("ordinal must be 1..364")
    remaining = ordinal
    for month, length in enumerate(MONTH_LENGTHS, start=1):
        if remaining <= length:
            return month, remaining
        remaining -= length
    raise AssertionError("unreachable")


def weekday_for_ordinal(ordinal: int, *, day001_weekday: str) -> str:
    if day001_weekday not in WEEKDAYS:
        raise ValueError("unknown weekday epoch")
    start = WEEKDAYS.index(day001_weekday)
    return WEEKDAYS[(start + ordinal - 1) % 7]


def weekday_for_date(month: int, day: int, *, day001_weekday: str) -> str:
    return weekday_for_ordinal(
        ordinal_day(month, day),
        day001_weekday=day001_weekday,
    )


def common_position(ordinal: int, *, day001_weekday: str) -> dict:
    month, day = month_day_from_ordinal(ordinal)
    quarter = ((ordinal - 1) // 91) + 1
    day_of_quarter = ((ordinal - 1) % 91) + 1
    week = ((ordinal - 1) // 7) + 1
    day_in_week = ((ordinal - 1) % 7) + 1
    return {
        "dayOfYear": ordinal,
        "month": month,
        "day": day,
        "quarter": quarter,
        "dayOfQuarter": day_of_quarter,
        "weekOfYear": week,
        "dayInWeek": day_in_week,
        "weekday": weekday_for_ordinal(
            ordinal, day001_weekday=day001_weekday
        ),
    }


def boundary_dates_for_common_date(
    *,
    opening_civil_date: dt.date,
    month: int,
    day: int,
) -> tuple[dt.date, dt.date]:
    """Return civil dates whose local sunsets open and close a Common date."""
    ordinal = ordinal_day(month, day)
    opens_on = opening_civil_date + dt.timedelta(days=ordinal - 1)
    closes_on = opens_on + dt.timedelta(days=1)
    return opens_on, closes_on


def position_from_boundary_date(
    *,
    opening_civil_date: dt.date,
    active_boundary_civil_date: dt.date,
    day001_weekday: str,
) -> dict:
    """Map a local sunset boundary date to the ordinary Common year.

    opening_civil_date is the civil date whose sunset opens Day 001.
    active_boundary_civil_date is the civil date of the sunset immediately
    preceding the observation instant.
    """
    offset = (active_boundary_civil_date - opening_civil_date).days
    ordinal = offset + 1
    if not 1 <= ordinal <= 364:
        raise ValueError("observation is outside the ordinary year")
    return common_position(ordinal, day001_weekday=day001_weekday)


def jubilee_year_state(cycle_year: int) -> dict:
    if not 1 <= cycle_year <= 50:
        raise ValueError("cycle_year must be 1..50")

    if cycle_year == 50:
        return {
            "cycleYear": 50,
            "sevenYearBlock": None,
            "yearWithinBlock": None,
            "isSabbaticalThreshold": False,
            "isJubileeYear": True,
            "releaseGate": {
                "month": 7,
                "day": 10,
                "name": "Day of Atonement",
            },
        }

    block = ((cycle_year - 1) // 7) + 1
    within = ((cycle_year - 1) % 7) + 1
    return {
        "cycleYear": cycle_year,
        "sevenYearBlock": block,
        "yearWithinBlock": within,
        "isSabbaticalThreshold": within == 7,
        "isJubileeYear": False,
        "releaseGate": None,
    }


def generate_cycle(*, first_common_year: int, day001_weekday: str) -> dict:
    validate_grid()
    years = []
    for cycle_year in range(1, 51):
        row = jubilee_year_state(cycle_year)
        row["commonYear"] = first_common_year + cycle_year - 1
        years.append(row)

    return {
        "version": "stillpoint-jubilee-v1-candidate",
        "ordinaryYearDays": 364,
        "monthLengths": list(MONTH_LENGTHS),
        "day001Weekday": day001_weekday,
        "fixedWeekdayAnchors": {
            "december10": weekday_for_date(
                12, 10, day001_weekday=day001_weekday
            ),
            "christmas": weekday_for_date(
                12, 25, day001_weekday=day001_weekday
            ),
            "atonement": weekday_for_date(
                7, 10, day001_weekday=day001_weekday
            ),
        },
        "years": years,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--first-common-year", required=True, type=int)
    parser.add_argument("--day001-weekday", default="Friday", choices=WEEKDAYS)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    output = generate_cycle(
        first_common_year=args.first_common_year,
        day001_weekday=args.day001_weekday,
    )
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
