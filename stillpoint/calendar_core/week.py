from __future__ import annotations

from datetime import datetime, timedelta

from .models import DuskProtocol, GeoPoint, WeeklyProtectedState
from .sunset import apparent_sunrise_utc, bracket_sunset


def named_day_for_boundary_civil_date(boundary_civil_date) -> str:
    return (boundary_civil_date + timedelta(days=1)).strftime("%A")


def protected_time_state(
    instant: datetime,
    *,
    location: GeoPoint,
    local_zone: str,
    protocol: DuskProtocol = DuskProtocol(),
) -> WeeklyProtectedState:
    if instant.tzinfo is None:
        raise ValueError("instant must be timezone-aware")

    pair = bracket_sunset(instant, location, local_zone, protocol)
    named_day = named_day_for_boundary_civil_date(pair.previous_civil_date)

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
        sunday_civil = pair.previous_civil_date + timedelta(days=1)
        sunrise = apparent_sunrise_utc(sunday_civil, location, protocol)
        instant_utc = instant.astimezone(sunrise.tzinfo)
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
