"""StillPoint platform-neutral calendar geometry and address domain.

Calendar Core owns sequence, dusk-boundary projection, the 364-day ordinary
address grid, Reconciliation address semantics, gates/phases, and weekly
protected-time geometry.

It does not enact ephemeris evidence, civic reference points, publications,
Jubilee epochs, or external-action authority.
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
from .models import (
    CalendarSnapshot,
    CommonDate,
    DuskProtocol,
    DualStamp,
    EnochPhase,
    GeoPoint,
    ReconciliationDecision,
    WeeklyProtectedState,
)
from .reconciliation import audit_reconciliation_schedule, forecast_reconciliation_weeks
from .service import CalendarConfig, get_calendar_snapshot
from .spec import ENGINEERING_INVARIANT, SPEC_VERSION, build_calendar_core_spec
from .sunset import apparent_sunrise_utc, apparent_sunset_utc, bracket_sunset
from .vectors import VECTORS_VERSION, build_calendar_projection_vectors
from .week import protected_time_state

__all__ = [
    "MONTH_LENGTHS",
    "GATE_SEQUENCE",
    "PHASE_LENGTHS",
    "SPEC_VERSION",
    "VECTORS_VERSION",
    "ENGINEERING_INVARIANT",
    "CalendarConfig",
    "CalendarSnapshot",
    "CommonDate",
    "DuskProtocol",
    "DualStamp",
    "EnochPhase",
    "GeoPoint",
    "ReconciliationDecision",
    "WeeklyProtectedState",
    "apparent_sunrise_utc",
    "apparent_sunset_utc",
    "audit_reconciliation_schedule",
    "boundary_dates_for_common_date",
    "bracket_sunset",
    "build_calendar_core_spec",
    "build_calendar_projection_vectors",
    "common_date",
    "forecast_reconciliation_weeks",
    "get_calendar_snapshot",
    "month_day_from_ordinal",
    "ordinal_day",
    "phase_for_base_day",
    "project_dual_stamp",
    "protected_time_state",
]
