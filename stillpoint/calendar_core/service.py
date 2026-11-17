from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from .dual_stamp import project_dual_stamp
from .gates import phase_for_base_day
from .jubilee import jubilee_state
from .models import CalendarSnapshot, GeoPoint
from .sunset import bracket_sunset
from .week import protected_time_state, protected_time_state_for_common_date
from .sacred import JUBILEE_EPOCH_COMMON_YEAR, JUBILEE_ROLLOVER_RULE


@dataclass(frozen=True)
class CalendarConfig:
    location: GeoPoint
    local_zone: str
    common_year: int
    opening_civil_date: date
    common_standard_offset_seconds: int
    continuous_k_at_opening: int = 0
    reference_rule_version: str = "immutable-364-v1"
    reference_station_id: Optional[str] = None
    ephemeris_id: Optional[str] = None
    jubilee_epoch_common_year: Optional[int] = JUBILEE_EPOCH_COMMON_YEAR
    jubilee_epoch_cycle: int = 1
    jubilee_rollover_rule: str = JUBILEE_ROLLOVER_RULE


def get_calendar_snapshot(
    instant: datetime, *, config: CalendarConfig
) -> CalendarSnapshot:
    dual = project_dual_stamp(
        instant,
        location=config.location,
        local_zone=config.local_zone,
        common_year=config.common_year,
        opening_civil_date=config.opening_civil_date,
        common_standard_offset_seconds=config.common_standard_offset_seconds,
        continuous_k_at_opening=config.continuous_k_at_opening,
    )
    pair = bracket_sunset(
        instant, config.location, config.local_zone
    )
    # The Common Calendar weekday—not the host Gregorian weekday—governs
    # the weekly civic rhythm once a finite Common-year projection exists.
    # External date stamps are used only for local-light measurement.
    if dual.common_date is not None:
        weekly = protected_time_state_for_common_date(
            instant,
            common_weekday=dual.common_date.weekday,
            projection_date=dual.common_standard_timestamp.date(),
            location=config.location,
        )
    else:
        weekly = protected_time_state(
            instant,
            location=config.location,
            local_zone=config.local_zone,
        )
    phase = (
        phase_for_base_day(dual.common_date.ordinal)
        if dual.common_date else None
    )
    jubilee = jubilee_state(
        common_year=config.common_year,
        epoch_common_year=config.jubilee_epoch_common_year,
        epoch_cycle=config.jubilee_epoch_cycle,
        rollover_rule=config.jubilee_rollover_rule,
    )
    return CalendarSnapshot(
        instant_utc=dual.instant_utc,
        civil_timestamp=dual.civil_timestamp,
        common_standard_timestamp=dual.common_standard_timestamp,
        local_sunset_previous=pair.previous,
        local_sunset_next=pair.next,
        continuous_k=dual.continuous_k,
        state=dual.state,
        common_date=dual.common_date,
        named_day=weekly.named_day,
        sabbath_active=weekly.is_sabbath,
        lords_day_active=weekly.is_lords_day,
        stillpoint_active=weekly.is_stillpoint,
        next_protected_boundary=weekly.next_protected_boundary,
        next_protected_boundary_label=weekly.next_protected_boundary_label,
        annual_phase=phase.phase if phase else None,
        solar_gate=phase.gate if phase else None,
        jubilee=jubilee,
        reference_rule_version=config.reference_rule_version,
        reference_station_id=config.reference_station_id,
        ephemeris_id=config.ephemeris_id,
        calendar_address=dual.calendar_address,
    )
