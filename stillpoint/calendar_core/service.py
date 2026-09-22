from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from .dual_stamp import project_dual_stamp
from .gates import phase_for_base_day
from .models import CalendarSnapshot, GeoPoint
from .sunset import bracket_sunset
from .week import protected_time_state


@dataclass(frozen=True)
class CalendarConfig:
    """Pure projection inputs.

    No reference-point authority, ephemeris authority, ratification status, or
    Jubilee epoch belongs here. Those jurisdictions live in downstream layers.
    """

    location: GeoPoint
    local_zone: str
    common_year: int
    opening_civil_date: date
    day001_weekday: str
    common_standard_offset_seconds: int
    reconciliation_days_after_completion: int = 0
    opening_continuous_k: int = 0


def get_calendar_snapshot(
    instant: datetime,
    *,
    config: CalendarConfig,
) -> CalendarSnapshot:
    dual = project_dual_stamp(
        instant,
        location=config.location,
        local_zone=config.local_zone,
        common_year=config.common_year,
        opening_civil_date=config.opening_civil_date,
        day001_weekday=config.day001_weekday,
        reconciliation_days_after_completion=config.reconciliation_days_after_completion,
        common_standard_offset_seconds=config.common_standard_offset_seconds,
        opening_continuous_k=config.opening_continuous_k,
    )
    pair = bracket_sunset(instant, config.location, config.local_zone)
    weekly = protected_time_state(
        instant,
        location=config.location,
        local_zone=config.local_zone,
    )

    phase = phase_for_base_day(dual.common_date.ordinal) if dual.common_date else None

    return CalendarSnapshot(
        instant_utc=dual.instant_utc,
        civil_timestamp=dual.civil_timestamp,
        common_standard_timestamp=dual.common_standard_timestamp,
        local_sunset_previous=pair.previous,
        local_sunset_next=pair.next,
        continuous_k=dual.continuous_k,
        state=dual.state,
        common_date=dual.common_date,
        ordinary_address=dual.ordinary_address,
        reconciliation_day=dual.reconciliation_day,
        reconciliation_address=dual.reconciliation_address,
        named_day=weekly.named_day,
        sabbath_active=weekly.is_sabbath,
        lords_day_active=weekly.is_lords_day,
        stillpoint_active=weekly.is_stillpoint,
        next_protected_boundary=weekly.next_protected_boundary,
        next_protected_boundary_label=weekly.next_protected_boundary_label,
        annual_phase=phase.phase if phase else None,
        solar_gate=phase.gate if phase else None,
    )
