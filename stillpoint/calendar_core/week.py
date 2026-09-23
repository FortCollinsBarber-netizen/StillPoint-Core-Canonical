from __future__ import annotations

from datetime import datetime, timedelta

from .models import DuskProtocol, GeoPoint, WeeklyProtectedState
from .sunset import apparent_sunrise_utc, apparent_sunset_utc, bracket_sunset


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



def protected_time_state_for_common_date(
    instant: datetime,
    *,
    common_weekday: str,
    projection_date,
    location: GeoPoint,
    protocol: DuskProtocol = DuskProtocol(),
) -> WeeklyProtectedState:
    """Resolve Sabbath/StillPoint from the fixed Common weekday plus local light.

    The Common Calendar weekday is authoritative for weekly rhythm. The
    projection date is used only to calculate local solar events for that
    canonical day; host Gregorian weekday identity has no authority here.
    """
    if instant.tzinfo is None:
        raise ValueError("instant must be timezone-aware")
    if common_weekday not in {
        "Sunday", "Monday", "Tuesday", "Wednesday",
        "Thursday", "Friday", "Saturday",
    }:
        raise ValueError("common_weekday must be a canonical weekday name")

    instant_utc = instant.astimezone(apparent_sunset_utc(
        projection_date, location, protocol
    ).tzinfo)
    sunrise = apparent_sunrise_utc(projection_date, location, protocol)
    sunset = apparent_sunset_utc(projection_date, location, protocol)

    if common_weekday == "Friday":
        if instant_utc >= sunset:
            next_sunset = apparent_sunset_utc(
                projection_date + timedelta(days=1), location, protocol
            )
            return WeeklyProtectedState(
                named_day="Saturday",
                is_sabbath=True,
                is_lords_day=False,
                is_stillpoint=True,
                next_protected_boundary=next_sunset,
                next_protected_boundary_label="SABBATH ENDS · LORD'S DAY BEGINS",
            )
        return WeeklyProtectedState(
            named_day="Friday",
            is_sabbath=False,
            is_lords_day=False,
            is_stillpoint=False,
            next_protected_boundary=sunset,
            next_protected_boundary_label="SABBATH BEGINS · STILLPOINT BEGINS",
        )

    if common_weekday == "Saturday":
        if instant_utc < sunset:
            return WeeklyProtectedState(
                named_day="Saturday",
                is_sabbath=True,
                is_lords_day=False,
                is_stillpoint=True,
                next_protected_boundary=sunset,
                next_protected_boundary_label="SABBATH ENDS · LORD'S DAY BEGINS",
            )
        sunday_sunrise = apparent_sunrise_utc(
            projection_date + timedelta(days=1), location, protocol
        )
        return WeeklyProtectedState(
            named_day="Sunday",
            is_sabbath=False,
            is_lords_day=True,
            is_stillpoint=True,
            next_protected_boundary=sunday_sunrise,
            next_protected_boundary_label="STILLPOINT RELEASE · SUNDAY SUNRISE",
        )

    if common_weekday == "Sunday":
        if instant_utc < sunrise:
            return WeeklyProtectedState(
                named_day="Sunday",
                is_sabbath=False,
                is_lords_day=True,
                is_stillpoint=True,
                next_protected_boundary=sunrise,
                next_protected_boundary_label="STILLPOINT RELEASE · SUNDAY SUNRISE",
            )
        if instant_utc < sunset:
            return WeeklyProtectedState(
                named_day="Sunday",
                is_sabbath=False,
                is_lords_day=True,
                is_stillpoint=False,
                next_protected_boundary=sunset,
                next_protected_boundary_label="LORD'S DAY ENDS · SUNDAY SUNSET",
            )

    return WeeklyProtectedState(
        named_day=common_weekday,
        is_sabbath=False,
        is_lords_day=False,
        is_stillpoint=False,
        next_protected_boundary=None,
        next_protected_boundary_label=None,
    )
