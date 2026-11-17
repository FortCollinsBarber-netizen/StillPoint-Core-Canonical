"""Read-only seven-day projection of an already-published Common Calendar week.

Week numbers are intrinsic to the fixed 364-day / 52-week Common Calendar.
The function does not consult the host Gregorian week, create company state,
select new calendar authority, or extend the finite publication.
"""

from __future__ import annotations

from typing import Any

from .runtime_surface import calendar_day_payload

WEEK_SCHEMA = "stillpoint.calendar-week.v1"
DAYS_PER_WEEK = 7
WEEKS_PER_YEAR = 52


def calendar_week_payload(year: int, week: int) -> dict[str, Any]:
    """Return exactly seven published Common dates in one immutable year.

    Invalid years and weeks fail closed. The result contains a deliberately
    bounded consumer projection; callers needing full per-day provenance can
    use the existing calendar_day_payload.
    """
    if type(year) is not int:
        raise ValueError("Common year must be an integer")
    if type(week) is not int or not 1 <= week <= WEEKS_PER_YEAR:
        raise ValueError("Common week must be an integer in 1..52")

    first_ordinal = (week - 1) * DAYS_PER_WEEK + 1
    last_ordinal = first_ordinal + DAYS_PER_WEEK - 1
    days: list[dict[str, Any]] = []
    first = None
    for ordinal in range(first_ordinal, last_ordinal + 1):
        payload = calendar_day_payload(year, ordinal)
        if first is None:
            first = payload
        common = payload["common_date"]
        if common["year"] != year or common["week"] != week:
            raise ValueError("Core published week does not match requested week")
        days.append({
            "calendar_address": payload["calendar_address"],
            "common_date": common,
            "civil_window": payload["civil_window"],
            "sacred_date": payload["sacred_date"],
            "observances": [
                {"id": item["id"], "name": item["name"],
                 "jurisdiction": item["jurisdiction"]}
                for item in payload["observances"]
            ],
            "is_sabbath_date": payload["protected_time"]["is_sabbath_date"],
        })

    assert first is not None
    return {
        "schema": WEEK_SCHEMA,
        "authority": "read-only-calendar-law",
        "calendar_namespace": "stillpoint.calendar_core",
        "year": year,
        "week": week,
        "day_count": DAYS_PER_WEEK,
        "first_address": days[0]["calendar_address"],
        "last_address": days[-1]["calendar_address"],
        "publication": first["publication"],
        "map": first["map"],
        "days": days,
    }
