from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .address import format_ordinary_address
from .calendar import common_date
from .models import DualStamp, GeoPoint


def project_dual_stamp(
    instant: datetime,
    *,
    location: GeoPoint,
    local_zone: str,
    common_year: int,
    opening_civil_date: date,
    common_standard_offset_seconds: int,
    continuous_k_at_opening: int = 0,
) -> DualStamp:
    if instant.tzinfo is None:
        raise ValueError("instant must be timezone-aware")
    if continuous_k_at_opening < 0:
        raise ValueError("continuous_k_at_opening must be >= 0")

    instant_utc = instant.astimezone(timezone.utc)
    common_tz = timezone(
        timedelta(seconds=common_standard_offset_seconds)
    )
    common_standard = instant_utc.astimezone(common_tz)
    offset = (common_standard.date() - opening_civil_date).days
    computed_k = continuous_k_at_opening + offset
    continuous_k = computed_k if computed_k >= 0 else None

    current = None
    calendar_address = None
    state = "OUTSIDE_RANGE"
    if 0 <= offset < 364:
        state = "ORDINARY"
        current = common_date(year=common_year, ordinal=offset + 1)
        calendar_address = format_ordinary_address(
            common_year, current.ordinal
        )

    civil = instant_utc.astimezone(ZoneInfo(local_zone))
    return DualStamp(
        instant_utc=instant_utc,
        civil_timestamp=civil,
        common_standard_timestamp=common_standard,
        continuous_k=continuous_k,
        state=state,
        common_date=current,
        calendar_address=calendar_address,
    )
