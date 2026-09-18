from __future__ import annotations

import math
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from .models import DuskProtocol, GeoPoint, SolarBoundaryPair

UTC = timezone.utc
DEFAULT_PROTOCOL = DuskProtocol()


def _norm_degrees(value: float) -> float:
    return value % 360.0


def _norm_hours(value: float) -> float:
    return value % 24.0


def _deg2rad(value: float) -> float:
    return math.radians(value)


def _rad2deg(value: float) -> float:
    return math.degrees(value)


def solar_event_utc(
    civil_date: date,
    location: GeoPoint,
    *,
    rising: bool,
    protocol: DuskProtocol = DEFAULT_PROTOCOL,
) -> datetime:
    """Return standardized apparent sunrise/sunset for a local civil date."""
    ordinal = civil_date.timetuple().tm_yday
    lng_hour = location.longitude / 15.0
    approximate_hour = 6.0 if rising else 18.0
    t = ordinal + ((approximate_hour - lng_hour) / 24.0)

    mean_anomaly = (0.9856 * t) - 3.289
    true_longitude = _norm_degrees(
        mean_anomaly
        + 1.916 * math.sin(_deg2rad(mean_anomaly))
        + 0.020 * math.sin(_deg2rad(2.0 * mean_anomaly))
        + 282.634
    )

    right_ascension = _norm_degrees(
        _rad2deg(math.atan(0.91764 * math.tan(_deg2rad(true_longitude))))
    )
    l_quadrant = math.floor(true_longitude / 90.0) * 90.0
    ra_quadrant = math.floor(right_ascension / 90.0) * 90.0
    right_ascension = (right_ascension + l_quadrant - ra_quadrant) / 15.0

    sin_declination = 0.39782 * math.sin(_deg2rad(true_longitude))
    cos_declination = math.cos(math.asin(sin_declination))
    cos_hour = (
        math.cos(_deg2rad(protocol.zenith_degrees))
        - sin_declination * math.sin(_deg2rad(location.latitude))
    ) / (cos_declination * math.cos(_deg2rad(location.latitude)))

    if not -1.0 <= cos_hour <= 1.0:
        raise ValueError(
            f"standardized {'sunrise' if rising else 'sunset'} unavailable "
            f"for {civil_date.isoformat()} at {location.id}"
        )

    hour_angle_degrees = _rad2deg(math.acos(cos_hour))
    if rising:
        hour_angle_degrees = 360.0 - hour_angle_degrees
    hour_angle = hour_angle_degrees / 15.0
    local_mean_time = hour_angle + right_ascension - (0.06571 * t) - 6.622
    local_mean_hours = _norm_hours(local_mean_time)

    utc_hours = local_mean_hours - lng_hour
    midnight = datetime.combine(civil_date, time(0, 0), tzinfo=UTC)
    return midnight + timedelta(hours=utc_hours)


def apparent_sunrise_utc(
    civil_date: date,
    location: GeoPoint,
    protocol: DuskProtocol = DEFAULT_PROTOCOL,
) -> datetime:
    return solar_event_utc(civil_date, location, rising=True, protocol=protocol)


def apparent_sunset_utc(
    civil_date: date,
    location: GeoPoint,
    protocol: DuskProtocol = DEFAULT_PROTOCOL,
) -> datetime:
    return solar_event_utc(civil_date, location, rising=False, protocol=protocol)


def bracket_sunset(
    instant: datetime,
    location: GeoPoint,
    local_zone: str,
    protocol: DuskProtocol = DEFAULT_PROTOCOL,
) -> SolarBoundaryPair:
    if instant.tzinfo is None:
        raise ValueError("instant must be timezone-aware")
    instant_utc = instant.astimezone(UTC)
    zone = ZoneInfo(local_zone)
    local_day = instant_utc.astimezone(zone).date()

    today = apparent_sunset_utc(local_day, location, protocol)
    if instant_utc >= today:
        next_day = local_day + timedelta(days=1)
        return SolarBoundaryPair(
            previous=today,
            next=apparent_sunset_utc(next_day, location, protocol),
            previous_civil_date=local_day,
            next_civil_date=next_day,
        )

    previous_day = local_day - timedelta(days=1)
    return SolarBoundaryPair(
        previous=apparent_sunset_utc(previous_day, location, protocol),
        next=today,
        previous_civil_date=previous_day,
        next_civil_date=local_day,
    )
