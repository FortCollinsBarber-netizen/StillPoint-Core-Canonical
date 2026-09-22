from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .calendar import common_date
from .models import DualStamp, GeoPoint
from .sunset import bracket_sunset


def project_dual_stamp(
    instant: datetime,
    *,
    location: GeoPoint,
    local_zone: str,
    common_year: int,
    opening_civil_date: date,
    day001_weekday: str,
    reconciliation_days_after_completion: int = 0,
    common_standard_offset_seconds: int,
    continuous_k_at_opening: int = 0,
) -> DualStamp:
    if instant.tzinfo is None:
        raise ValueError("instant must be timezone-aware")
    if reconciliation_days_after_completion not in (0, 7):
        raise ValueError("reconciliation must be 0 or 7 days")

    instant_utc = instant.astimezone(timezone.utc)
    pair = bracket_sunset(instant_utc, location, local_zone)
    offset = (pair.previous_civil_date - opening_civil_date).days

    current = None
    reconciliation_day = None
    reconciliation_address = None
    state = "OUTSIDE_RANGE"

    if 0 <= offset < 364:
        state = "ORDINARY"
        current = common_date(
            year=common_year,
            ordinal=offset + 1,
            day001_weekday=day001_weekday,
        )
    elif 364 <= offset < 364 + reconciliation_days_after_completion:
        state = "RECONCILIATION"
        reconciliation_day = offset - 364 + 1
        reconciliation_address = (
            f"Y_{common_year}/Y_{common_year + 1}-R{reconciliation_day}"
        )

    civil = instant_utc.astimezone(ZoneInfo(local_zone))
    common_tz = timezone(timedelta(seconds=common_standard_offset_seconds))
    common_standard = instant_utc.astimezone(common_tz)

    return DualStamp(
        instant_utc=instant_utc,
        civil_timestamp=civil,
        common_standard_timestamp=common_standard,
        continuous_k=continuous_k_at_opening + offset,
        state=state,
        common_date=current,
        reconciliation_day=reconciliation_day,
        reconciliation_address=reconciliation_address,
    )
