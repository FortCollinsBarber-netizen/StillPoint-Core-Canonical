from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .calendar import WEEKDAYS
from .models import DuskProtocol, GeoPoint, WeeklyProtectedState
from .sunset import (
    apparent_sunset_utc,
    bracket_sunset,
    civil_dawn_utc,
    civil_dusk_utc,
)


def named_day_for_boundary_civil_date(boundary_civil_date) -> str:
    """Legacy physical weekday label; not authoritative for a Common date."""
    return (boundary_civil_date + timedelta(days=1)).strftime("%A")


def protected_time_state(
    instant: datetime,
    *,
    location: GeoPoint,
    local_zone: str,
    protocol: DuskProtocol = DuskProtocol(),
) -> WeeklyProtectedState:
    """Legacy local physical-weekday projection.

    Sacred Sabbath follows apparent sunset. Civic StillPoint begins at Friday
    civil dusk and releases at Sunday civil dawn. For authoritative Common
    weekdays use protected_time_state_for_common_date below.
    """
    if instant.tzinfo is None:
        raise ValueError("instant must be timezone-aware")

    instant_utc = instant.astimezone(timezone.utc)
    pair = bracket_sunset(instant, location, local_zone, protocol)
    named_day = named_day_for_boundary_civil_date(pair.previous_civil_date)

    if named_day == "Saturday":
        civic_open = civil_dusk_utc(pair.previous_civil_date, location)
        if instant_utc < civic_open:
            return WeeklyProtectedState(
                named_day=named_day,
                is_sabbath=True,
                is_lords_day=False,
                is_stillpoint=False,
                next_protected_boundary=civic_open,
                next_protected_boundary_label="STILLPOINT BEGINS · FRIDAY CIVIL DUSK",
            )
        return WeeklyProtectedState(
            named_day=named_day,
            is_sabbath=True,
            is_lords_day=False,
            is_stillpoint=True,
            next_protected_boundary=pair.next,
            next_protected_boundary_label="SABBATH ENDS · LORD'S DAY BEGINS",
        )

    if named_day == "Sunday":
        sunday_projection = pair.previous_civil_date + timedelta(days=1)
        civic_release = civil_dawn_utc(sunday_projection, location)
        if instant_utc < civic_release:
            return WeeklyProtectedState(
                named_day=named_day,
                is_sabbath=False,
                is_lords_day=True,
                is_stillpoint=True,
                next_protected_boundary=civic_release,
                next_protected_boundary_label="STILLPOINT RELEASE · SUNDAY CIVIL DAWN",
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
    """Common-weekday-authoritative weekly protection with independent light.

    External Gregorian dates provide astronomical measurements, not weekday
    authority. Civil StillPoint uses -6-degree civil twilight; sacred Sabbath
    and Lord's Day continue using apparent sunset. Neither changes Common dates.
    """
    if instant.tzinfo is None:
        raise ValueError("instant must be timezone-aware")
    if common_weekday not in WEEKDAYS:
        raise ValueError("common_weekday must be a canonical weekday name")

    instant_utc = instant.astimezone(timezone.utc)
    sunset = apparent_sunset_utc(projection_date, location, protocol)
    weekday_index = WEEKDAYS.index(common_weekday)
    next_weekday = WEEKDAYS[(weekday_index + 1) % 7]
    creation_named_day = next_weekday if instant_utc >= sunset else common_weekday

    if common_weekday == "Friday":
        civic_open = civil_dusk_utc(projection_date, location)
        if instant_utc < sunset:
            return WeeklyProtectedState(
                named_day="Friday",
                is_sabbath=False,
                is_lords_day=False,
                is_stillpoint=False,
                next_protected_boundary=sunset,
                next_protected_boundary_label="SABBATH BEGINS · FRIDAY SUNSET",
            )
        if instant_utc < civic_open:
            return WeeklyProtectedState(
                named_day="Saturday",
                is_sabbath=True,
                is_lords_day=False,
                is_stillpoint=False,
                next_protected_boundary=civic_open,
                next_protected_boundary_label="STILLPOINT BEGINS · FRIDAY CIVIL DUSK",
            )
        return WeeklyProtectedState(
            named_day="Saturday",
            is_sabbath=True,
            is_lords_day=False,
            is_stillpoint=True,
            next_protected_boundary=apparent_sunset_utc(
                projection_date + timedelta(days=1), location, protocol
            ),
            next_protected_boundary_label="SABBATH ENDS · LORD'S DAY BEGINS",
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
        sunday_dawn = civil_dawn_utc(
            projection_date + timedelta(days=1), location
        )
        return WeeklyProtectedState(
            named_day="Sunday",
            is_sabbath=False,
            is_lords_day=True,
            is_stillpoint=True,
            next_protected_boundary=sunday_dawn,
            next_protected_boundary_label="STILLPOINT RELEASE · SUNDAY CIVIL DAWN",
        )

    if common_weekday == "Sunday":
        sunday_dawn = civil_dawn_utc(projection_date, location)
        if instant_utc < sunday_dawn:
            return WeeklyProtectedState(
                named_day="Sunday",
                is_sabbath=False,
                is_lords_day=True,
                is_stillpoint=True,
                next_protected_boundary=sunday_dawn,
                next_protected_boundary_label="STILLPOINT RELEASE · SUNDAY CIVIL DAWN",
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
        named_day=creation_named_day,
        is_sabbath=False,
        is_lords_day=False,
        is_stillpoint=False,
        next_protected_boundary=None,
        next_protected_boundary_label=None,
    )
