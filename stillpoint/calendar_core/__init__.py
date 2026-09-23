"""StillPoint platform-neutral fixed calendar and clock domain.

Calendar Core owns the ratified 364-day / 52-week sacred-civic address grid.
Astronomy, civil translation, witness layers, Jubilee, and historical reference
rules may describe the grid but cannot move it or add an interannual day.
"""

from .address import (
    CalendarAddress,
    format_ordinary_address,
    format_reconciliation_address,
    parse_calendar_address,
)
from .appointments import (
    AppointedTime,
    AppointedTimeOccurrence,
    project_appointed_time,
)
from .artifact_manifest import (
    ARTIFACT_MANIFEST_VERSION,
    build_calendar_core_artifact_manifest,
    canonical_export_bytes,
    export_calendar_core_artifact_manifest,
)
from .astronomy import (
    AstronomyEvidence,
    AstronomyEvidenceError,
    AstronomyProvider,
    MappingAstronomyProvider,
)
from .calendar import (
    DAY001_WEEKDAY,
    MONTH_LENGTHS,
    boundary_dates_for_common_date,
    common_date,
    month_day_from_ordinal,
    ordinal_day,
)
from .dual_stamp import project_dual_stamp
from .gates import GATE_SEQUENCE, PHASE_LENGTHS, phase_for_base_day
from .jubilee import (
    JubileeReleaseGate,
    jubilee_release_gate,
    jubilee_state,
)
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
from .projection_vectors import (
    PROJECTION_VECTOR_VERSION,
    build_calendar_projection_vectors,
)
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
from .reconciliation import (
    audit_reconciliation_schedule,
    forecast_reconciliation_weeks,
)
from .reference_rule import (
    SPRING_GATE_ORDINAL,
    select_v32_nearest_legal,
    select_v33_nearest_spring_gate,
    select_v33_nearest_spring_gate_from_evidence,
    select_v33_nearest_spring_gate_from_provider,
)
from .sacred_map import (
    DEFAULT_CYCLE_YEARS,
    MAP_VERSION,
    Observance,
    address_for,
    build_sacred_civic_map,
    export_sacred_civic_map,
    resolved_observances,
)
from .service import CalendarConfig, get_calendar_snapshot
from .spec import (
    SPEC_VERSION,
    CalendarSpecValidationError,
    build_calendar_core_spec,
    validate_calendar_core_spec,
)
from .sunset import (
    apparent_sunrise_utc,
    apparent_sunset_utc,
    bracket_sunset,
)
from .week import protected_time_state
from .witness import (
    LunarWitness,
    SeasonGateWitness,
    WitnessValidationError,
    as_march_equinox_evidence,
)

__all__ = [
    "DAY001_WEEKDAY",
    "MONTH_LENGTHS",
    "GATE_SEQUENCE",
    "PHASE_LENGTHS",
    "SPRING_GATE_ORDINAL",
    "SPEC_VERSION",
    "MAP_VERSION",
    "DEFAULT_CYCLE_YEARS",
    "PROJECTION_VECTOR_VERSION",
    "PUBLICATION_VERSION",
    "ALLOWED_AUTHORITY_STATUSES",
    "ALLOWED_RECONCILIATION_DAYS",
    "CalendarAddress",
    "AppointedTime",
    "AppointedTimeOccurrence",
    "Observance",
    "ARTIFACT_MANIFEST_VERSION",
    "AstronomyEvidence",
    "AstronomyEvidenceError",
    "AstronomyProvider",
    "MappingAstronomyProvider",
    "CalendarConfig",
    "CalendarSnapshot",
    "CalendarSpecValidationError",
    "CommonDate",
    "DuskProtocol",
    "DualStamp",
    "EnochPhase",
    "GeoPoint",
    "JubileeState",
    "JubileeReleaseGate",
    "LunarWitness",
    "SeasonGateWitness",
    "WitnessValidationError",
    "PublicationEnvelope",
    "PublicationRange",
    "PublicationValidationError",
    "ReconciliationDecision",
    "WeeklyProtectedState",
    "address_for",
    "apparent_sunrise_utc",
    "apparent_sunset_utc",
    "audit_reconciliation_schedule",
    "boundary_dates_for_common_date",
    "bracket_sunset",
    "build_calendar_core_artifact_manifest",
    "build_calendar_core_spec",
    "build_calendar_projection_vectors",
    "build_sacred_civic_map",
    "canonical_export_bytes",
    "canonical_publication_bytes",
    "common_date",
    "export_calendar_core_artifact_manifest",
    "export_sacred_civic_map",
    "forecast_reconciliation_weeks",
    "format_ordinary_address",
    "format_reconciliation_address",
    "get_calendar_snapshot",
    "jubilee_release_gate",
    "jubilee_state",
    "month_day_from_ordinal",
    "ordinal_day",
    "parse_calendar_address",
    "phase_for_base_day",
    "project_dual_stamp",
    "project_appointed_time",
    "protected_time_state",
    "publication_digest",
    "resolved_observances",
    "select_v32_nearest_legal",
    "select_v33_nearest_spring_gate",
    "select_v33_nearest_spring_gate_from_evidence",
    "select_v33_nearest_spring_gate_from_provider",
    "as_march_equinox_evidence",
    "validate_calendar_core_spec",
    "validate_publication_document",
    "validate_publication_rows",
]
