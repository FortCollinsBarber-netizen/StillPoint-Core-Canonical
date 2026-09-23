from __future__ import annotations

from datetime import date, datetime, timedelta

from .calendar import WEEKDAYS
from .models import DuskProtocol, GeoPoint, WeeklyProtectedState
from .sunset import apparent_sunrise_utc, apparent_sunset_utc, bracket_sunset


def _next_weekday(name: str) -> str:
    try:
        index = WEEKDAYS.index(name)
    except ValueError as exc:
        raise ValueError(f"unsupported Common Calendar weekday: {name}") from exc
    return WEEKDAYS[(index + 1) % len(WEEKDAYS)]


def protected_time_state(
    instant: datetime,
    *,
    location: GeoPoint,
    local_zone: str,
    common_weekday: str | None = None,
    common_standard_civil_date: date | None = None,
    protocol: DuskProtocol = DuskProtocol(),
) -> WeeklyProtectedState:
    if instant.tzinfo is None:
        raise ValueError("instant must be timezone-aware")

    if common_weekday is None or common_standard_civil_date is None:
        return WeeklyProtectedState(
            named_day="COMMON DAY",
            is_sabbath=False,
            is_lords_day=False,
            is_stillpoint=False,
            next_protected_boundary=None,
            next_protected_boundary_label=None,
        )

    pair = bracket_sunset(instant, location, local_zone, protocol)
    today_sunset = apparent_sunset_utc(
        common_standard_civil_date,
        location,
        protocol,
    )
    instant_utc = instant.astimezone(today_sunset.tzinfo)
    after_sunset = instant_utc >= today_sunset

    named_day = (
        _next_weekday(common_weekday)
        if after_sunset
        else common_weekday
    )
    sacred_civil_date = (
        common_standard_civil_date + timedelta(days=1)
        if after_sunset
        else common_standard_civil_date
    )

    if named_day == "Saturday":
        return WeeklyProtectedState(
            named_day=named_day,
            is_sabbath=True,
            is_lords_day=False,
            is_stillpoint=True,
            next_protected_boundary=pair.next,
            next_protected_boundary_label="SABBATH ENDS · LORD'S DAY BEGINS",
        )

    if named_day == "Sunday":
        sunrise = apparent_sunrise_utc(
            sacred_civil_date,
            location,
            protocol,
        )
        if instant_utc < sunrise:
            return WeeklyProtectedState(
                named_day=named_day,
                is_sabbath=False,
                is_lords_day=True,
                is_stillpoint=True,
                next_protected_boundary=sunrise,
                next_protected_boundary_label="STILLPOINT RELEASE · SUNDAY SUNRISE",
            )
        return WeeklyProtectedState(
            named_day=named_day,
            is_sabbath=False,
            is_lords_day=True,
            is_stillpoint=False,
            next_protected_boundary=pair.next,
            next_protected_boundary_label="LORD'S DAY ENDS · SUNDAY SUNSET",
        )

    return WeeklyProtectedState(
        named_day=named_day,
        is_sabbath=False,
        is_lords_day=False,
        is_stillpoint=False,
        next_protected_boundary=None,
        next_protected_boundary_label=None,
    )
