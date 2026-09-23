"""StillPoint platform-neutral calendar and clock domain.

Calendar Core owns temporal geometry and calendar-domain mathematics. It is
separate from stillpoint.temporal, which owns continuing-evidence and action
authority. A finite calendar publication is an evidence object; importing this
package does not ratify one.
"""

from .address import (
    CalendarAddress,
    format_ordinary_address,
    parse_calendar_address,
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
    MONTH_LENGTHS,
    boundary_dates_for_common_date,
    common_date,
    month_day_from_ordinal,
    ordinal_day,
)
from .dual_stamp import project_dual_stamp
from .governor import (
    ANCHOR_WEEKDAY,
    CANONICAL_FIRST_YEAR,
    CANONICAL_LAST_YEAR,
    CANONICAL_TOTAL_DAYS,
    CANONICAL_WEEKS,
    CANONICAL_YEAR_COUNT,
    CANONICAL_YEAR_DAYS,
    FORBIDDEN_DATES,
    RHYTHM_GOVERNOR,
    CalendarInvariantViolation,
    CanonicalDate,
    RhythmAuthority,
    RhythmDecision,
    RhythmGovernor,
    RhythmRequest,
    assert_canonical_surface,
    validate_transition,
)
from .overlays import (
    ALL_OVERLAY_KINDS,
    CANONICAL_OVERLAY_KINDS,
    WITNESS_OVERLAY_KINDS,
    OVERLAY_POLICY_VERSION,
    OverlayRecord,
    grid_identity,
    inhabit_surface,
    overlay_policy_payload,
)
from .observances import (
    ALL_OBSERVANCES,
    CIVIC_OBSERVANCES,
    MONTH_OPENINGS,
    SACRED_OBSERVANCES,
    Observance,
    observances_for_ordinal,
)
from .population import (
    PopulationAddress,
    address as population_address,
    address_from_ordinal as population_address_from_ordinal,
    iter_fifty_year_map,
    iter_year as iter_population_year,
)
from .population_artifact import (
    POPULATION_ARTIFACT_VERSION,
    build_calendar_population_artifact,
    export_calendar_population_artifact,
)
from .appointments import (
    AppointedTime,
    AppointedTimeOccurrence,
    project_appointed_time,
)
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
    WeeklyProtectedState,
)
from .projection_vectors import (
    PROJECTION_VECTOR_VERSION,
    build_calendar_projection_vectors,
)
from .publication import (
    ALLOWED_AUTHORITY_STATUSES,
    PUBLICATION_VERSION,
    PublicationEnvelope,
    PublicationRange,
    PublicationValidationError,
    canonical_publication_bytes,
    publication_digest,
    validate_publication_document,
    validate_publication_rows,
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
from .witness_overlays import (
    ALL_EXTERNAL_WITNESSES,
    EXTERNAL_WITNESS_ARTIFACT_VERSION,
    ISLAMIC_2026,
    JEWISH_2026,
    OVERLAY_SCHEMA as EXTERNAL_WITNESS_SCHEMA,
    ExternalCalendarWitness,
    build_external_witness_artifact,
    export_external_witness_artifact,
    witnesses_for_external_date,
)

__all__ = [
    "MONTH_LENGTHS",
    "ANCHOR_WEEKDAY",
    "CANONICAL_YEAR_DAYS",
    "CANONICAL_WEEKS",
    "CANONICAL_TOTAL_DAYS",
    "CalendarInvariantViolation",
    "CanonicalDate",
    "RHYTHM_GOVERNOR",
    "RhythmAuthority",
    "RhythmDecision",
    "RhythmGovernor",
    "RhythmRequest",
    "assert_canonical_surface",
    "validate_transition",
    "OVERLAY_POLICY_VERSION",
    "CANONICAL_OVERLAY_KINDS",
    "WITNESS_OVERLAY_KINDS",
    "ALL_OVERLAY_KINDS",
    "OverlayRecord",
    "grid_identity",
    "inhabit_surface",
    "overlay_policy_payload",
    "CANONICAL_FIRST_YEAR",
    "CANONICAL_LAST_YEAR",
    "CANONICAL_YEAR_COUNT",
    "FORBIDDEN_DATES",
    "GATE_SEQUENCE",
    "PHASE_LENGTHS",
    "SPEC_VERSION",
    "PROJECTION_VECTOR_VERSION",
    "PUBLICATION_VERSION",
    "ALLOWED_AUTHORITY_STATUSES",
    "POPULATION_ARTIFACT_VERSION",
    "Observance",
    "PopulationAddress",
    "ALL_OBSERVANCES",
    "SACRED_OBSERVANCES",
    "CIVIC_OBSERVANCES",
    "MONTH_OPENINGS",
    "CalendarAddress",
    "AppointedTime",
    "AppointedTimeOccurrence",
    "format_ordinary_address",
    "parse_calendar_address",
    "ARTIFACT_MANIFEST_VERSION",
    "build_calendar_core_artifact_manifest",
    "canonical_export_bytes",
    "export_calendar_core_artifact_manifest",
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
    "WeeklyProtectedState",
    "apparent_sunrise_utc",
    "apparent_sunset_utc",
    "boundary_dates_for_common_date",
    "bracket_sunset",
    "build_calendar_core_spec",
    "build_calendar_projection_vectors",
    "canonical_publication_bytes",
    "common_date",
    "get_calendar_snapshot",
    "jubilee_state",
    "month_day_from_ordinal",
    "ordinal_day",
    "phase_for_base_day",
    "project_dual_stamp",
    "project_appointed_time",
    "jubilee_release_gate",
    "as_march_equinox_evidence",
    "protected_time_state",
    "publication_digest",
    "validate_calendar_core_spec",
    "validate_publication_document",
    "validate_publication_rows",
    "observances_for_ordinal",
    "population_address",
    "population_address_from_ordinal",
    "iter_population_year",
    "iter_fifty_year_map",
    "build_calendar_population_artifact",
    "export_calendar_population_artifact",
    "ExternalCalendarWitness",
    "EXTERNAL_WITNESS_SCHEMA",
    "EXTERNAL_WITNESS_ARTIFACT_VERSION",
    "JEWISH_2026",
    "ISLAMIC_2026",
    "ALL_EXTERNAL_WITNESSES",
    "witnesses_for_external_date",
    "build_external_witness_artifact",
    "export_external_witness_artifact",
]
