"""StillPoint platform-neutral calendar and clock domain.

Calendar Core owns temporal geometry and calendar-domain mathematics. It is
separate from stillpoint.temporal, which owns continuing-evidence and action
authority. A finite calendar publication is an evidence object; importing this
package does not ratify one.
"""

from .address import (\n    CalendarAddress,\n    format_ordinary_address,\n    format_reconciliation_address,\n    parse_calendar_address,\n)\nfrom .astronomy import (
    AstronomyEvidence,
    AstronomyEvidenceError,
    AstronomyProvider,
    MappingAstronomyProvider,
)
from .calendar import MONTH_LENGTHS, boundary_dates_for_common_date, common_date, month_day_from_ordinal, ordinal_day
from .dual_stamp import project_dual_stamp
from .gates import GATE_SEQUENCE, PHASE_LENGTHS, phase_for_base_day
from .jubilee import jubilee_state
from .models import CalendarSnapshot, CommonDate, DuskProtocol, DualStamp, EnochPhase, GeoPoint, JubileeState, ReconciliationDecision, WeeklyProtectedState
from .projection_vectors import PROJECTION_VECTOR_VERSION, build_calendar_projection_vectors
from .publication import (
    ALLOWED_AUTHORITY_STATUSES,
    ALLOWED_RECONCILIATION_DAYS,
    PUBLICATION_VERSION,
    PublicationEnvelope,
    PublicationRange,
    PublicationValidationError,
    canonical_publication_bytes,
    publication_digest,
    validate_publication_document,
    validate_publication_rows,
)
from .reconciliation import audit_reconciliation_schedule, forecast_reconciliation_weeks
from .reference_rule import (
    SPRING_GATE_ORDINAL,
    select_v32_nearest_legal,
    select_v33_nearest_spring_gate,
    select_v33_nearest_spring_gate_from_evidence,
    select_v33_nearest_spring_gate_from_provider,
)
from .service import CalendarConfig, get_calendar_snapshot
from .spec import (
    SPEC_VERSION,
    CalendarSpecValidationError,
    build_calendar_core_spec,
    validate_calendar_core_spec,
)
from .sunset import apparent_sunrise_utc, apparent_sunset_utc, bracket_sunset
from .week import protected_time_state

__all__ = [
    "MONTH_LENGTHS", "GATE_SEQUENCE", "PHASE_LENGTHS", "SPRING_GATE_ORDINAL",
    "SPEC_VERSION", "PROJECTION_VECTOR_VERSION", "PUBLICATION_VERSION",
    "ALLOWED_AUTHORITY_STATUSES", "ALLOWED_RECONCILIATION_DAYS",\n    "CalendarAddress", "format_ordinary_address",\n    "format_reconciliation_address", "parse_calendar_address",
    "AstronomyEvidence", "AstronomyEvidenceError", "AstronomyProvider",
    "MappingAstronomyProvider", "CalendarConfig", "CalendarSnapshot",
    "CalendarSpecValidationError", "CommonDate", "DuskProtocol", "DualStamp",
    "EnochPhase", "GeoPoint", "JubileeState", "PublicationEnvelope",
    "PublicationRange", "PublicationValidationError", "ReconciliationDecision",
    "WeeklyProtectedState", "apparent_sunrise_utc", "apparent_sunset_utc",
    "audit_reconciliation_schedule", "boundary_dates_for_common_date",
    "bracket_sunset", "build_calendar_core_spec",
    "build_calendar_projection_vectors", "canonical_publication_bytes",
    "common_date", "forecast_reconciliation_weeks", "get_calendar_snapshot",
    "jubilee_state", "month_day_from_ordinal", "ordinal_day",
    "phase_for_base_day", "project_dual_stamp", "protected_time_state",
    "publication_digest", "select_v32_nearest_legal",
    "select_v33_nearest_spring_gate",
    "select_v33_nearest_spring_gate_from_evidence",
    "select_v33_nearest_spring_gate_from_provider",
    "validate_calendar_core_spec", "validate_publication_document",
    "validate_publication_rows",
]
