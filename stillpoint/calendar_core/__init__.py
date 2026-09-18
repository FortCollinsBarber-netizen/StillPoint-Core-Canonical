"""StillPoint platform-neutral calendar and clock domain.

This package is deliberately separate from stillpoint.temporal, which already
owns the continuing-evidence and temporal-authority domain. Calendar law and
epistemic temporal authority are related but neither owns the other.
"""

from .calendar import (
    MONTH_LENGTHS,
    boundary_dates_for_common_date,
    common_date,
    month_day_from_ordinal,
    ordinal_day,
)
from .dual_stamp import project_dual_stamp
from .gates import GATE_SEQUENCE, PHASE_LENGTHS, phase_for_base_day
from .jubilee import jubilee_state
from .models import (
    CalendarSnapshot,
    CommonDate,
    DuskProtocol,
    DualStamp,
    EnochPhase,
    GeoPoint,
    JubileeState,
    ReconciliationDecision,
    WeeklyProtectedState,
)
from .reconciliation import audit_reconciliation_schedule, forecast_reconciliation_weeks
from .reference_rule import (
    SPRING_GATE_ORDINAL,
    select_v32_nearest_legal,
    select_v33_nearest_spring_gate,
)
from .service import CalendarConfig, get_calendar_snapshot
from .sunset import apparent_sunrise_utc, apparent_sunset_utc, bracket_sunset
from .week import protected_time_state

__all__ = [
    "MONTH_LENGTHS",
    "GATE_SEQUENCE",
    "PHASE_LENGTHS",
    "SPRING_GATE_ORDINAL",
    "CalendarConfig",
    "CalendarSnapshot",
    "CommonDate",
    "DuskProtocol",
    "DualStamp",
    "EnochPhase",
    "GeoPoint",
    "JubileeState",
    "ReconciliationDecision",
    "WeeklyProtectedState",
    "apparent_sunrise_utc",
    "apparent_sunset_utc",
    "audit_reconciliation_schedule",
    "boundary_dates_for_common_date",
    "bracket_sunset",
    "common_date",
    "forecast_reconciliation_weeks",
    "get_calendar_snapshot",
    "jubilee_state",
    "month_day_from_ordinal",
    "ordinal_day",
    "phase_for_base_day",
    "project_dual_stamp",
    "protected_time_state",
    "select_v32_nearest_legal",
    "select_v33_nearest_spring_gate",
]
