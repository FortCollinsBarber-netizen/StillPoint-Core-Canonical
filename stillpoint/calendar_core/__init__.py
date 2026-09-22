"""StillPoint platform-neutral calendar and clock domain.

Calendar Core owns temporal geometry and calendar-domain mathematics. It is
separate from stillpoint.temporal, which owns continuing-evidence and action
authority. A finite calendar publication is an evidence object; importing this
package does not ratify one.
"""

from .calendar import MONTH_LENGTHS, boundary_dates_for_common_date, common_date, month_day_from_ordinal, ordinal_day
from .dual_stamp import project_dual_stamp
from .gates import GATE_SEQUENCE, PHASE_LENGTHS, phase_for_base_day
from .jubilee import jubilee_state
from .models import CalendarSnapshot, CommonDate, DuskProtocol, DualStamp, EnochPhase, GeoPoint, JubileeState, ReconciliationDecision, WeeklyProtectedState
from .projection_vectors import PROJECTION_VECTOR_VERSION, build_calendar_projection_vectors
from .publication import ALLOWED_RECONCILIATION_DAYS, PublicationRange, PublicationValidationError, validate_publication_rows
from .reconciliation import audit_reconciliation_schedule, forecast_reconciliation_weeks
from .reference_rule import SPRING_GATE_ORDINAL, select_v32_nearest_legal, select_v33_nearest_spring_gate
from .service import CalendarConfig, get_calendar_snapshot
from .spec import SPEC_VERSION, build_calendar_core_spec
from .sunset import apparent_sunrise_utc, apparent_sunset_utc, bracket_sunset
from .week import protected_time_state

__all__ = [
    "MONTH_LENGTHS", "GATE_SEQUENCE", "PHASE_LENGTHS", "SPRING_GATE_ORDINAL",
    "SPEC_VERSION", "PROJECTION_VECTOR_VERSION", "ALLOWED_RECONCILIATION_DAYS",
    "CalendarConfig", "CalendarSnapshot", "CommonDate", "DuskProtocol", "DualStamp",
    "EnochPhase", "GeoPoint", "JubileeState", "PublicationRange",
    "PublicationValidationError", "ReconciliationDecision", "WeeklyProtectedState",
    "apparent_sunrise_utc", "apparent_sunset_utc", "audit_reconciliation_schedule",
    "boundary_dates_for_common_date", "bracket_sunset", "build_calendar_core_spec",
    "build_calendar_projection_vectors", "common_date", "forecast_reconciliation_weeks",
    "get_calendar_snapshot", "jubilee_state", "month_day_from_ordinal", "ordinal_day",
    "phase_for_base_day", "project_dual_stamp", "protected_time_state",
    "select_v32_nearest_legal", "select_v33_nearest_spring_gate",
    "validate_publication_rows",
]
