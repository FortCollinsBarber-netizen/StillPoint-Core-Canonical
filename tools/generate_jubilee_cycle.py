#!/usr/bin/env python3
"""Deterministic StillPoint Jubilee / fixed-date calendar helpers.

This module does not select the astronomical annual epoch. It operates on an
already-enacted year sequence and a separately enacted weekday epoch.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

MONTH_LENGTHS = (30, 30, 31) * 4
MONTH_NAMES = (
    "January", "February", "March",
    "April", "May", "June",
    "July", "August", "September",
    "October", "November", "December",
)
WEEKDAYS = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")


def validate_grid() -> None:
    if sum(MONTH_LENGTHS) != 364:
        raise RuntimeError("ordinary year must contain exactly 364 days")
    if any(sum(MONTH_LENGTHS[q:q+3]) != 91 for q in range(0, 12, 3)):
        raise RuntimeError("each quarter must contain exactly 91 days")


def ordinal_day(month: int, day: int) -> int:
    validate_grid()
    if not 1 <= month <= 12:
        raise ValueError("month must be 1..12")
    length = MONTH_LENGTHS[month - 1]
    if not 1 <= day <= length:
        raise ValueError(f"day must be 1..{length} for month {month}")
    return sum(MONTH_LENGTHS[:month - 1]) + day


def weekday_for_date(month: int, day: int, *, day001_weekday: str) -> str:
    if day001_weekday not in WEEKDAYS:
        raise ValueError("unknown weekday epoch")
    start = WEEKDAYS.index(day001_weekday)
    offset = ordinal_day(month, day) - 1
    return WEEKDAYS[(start + offset) % 7]


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
            "releaseGate": {"month": 7, "day": 10, "name": "Day of Atonement"}
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

    anchors = {
        "december10": weekday_for_date(12, 10, day001_weekday=day001_weekday),
        "christmas": weekday_for_date(12, 25, day001_weekday=day001_weekday),
        "atonement": weekday_for_date(7, 10, day001_weekday=day001_weekday),
    }

    return {
        "version": "stillpoint-jubilee-v1-candidate",
        "ordinaryYearDays": 364,
        "monthLengths": list(MONTH_LENGTHS),
        "day001Weekday": day001_weekday,
        "fixedWeekdayAnchors": anchors,
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
