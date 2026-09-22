from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass(frozen=True)
class GeoPoint:
    latitude: float
    longitude: float
    id: str = "LOCAL"

    def __post_init__(self) -> None:
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError("latitude must be within [-90, 90]")
        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError("longitude must be within [-180, 180]")


@dataclass(frozen=True)
class DuskProtocol:
    id: str = "apparent-sunrise-set-0.8333"
    zenith_degrees: float = 90.8333


@dataclass(frozen=True)
class SolarBoundaryPair:
    previous: datetime
    next: datetime
    previous_civil_date: date
    next_civil_date: date


@dataclass(frozen=True)
class EnochPhase:
    phase: int
    gate: int
    motion: str
    days: int
    start_ordinal: int
    end_ordinal: int


@dataclass(frozen=True)
class CommonDate:
    year: int
    ordinal: int
    month: int
    day: int
    quarter: int
    day_of_quarter: int
    week: int
    day_in_week: int
    weekday: str


@dataclass(frozen=True)
class WeeklyProtectedState:
    named_day: str
    is_sabbath: bool
    is_lords_day: bool
    is_stillpoint: bool
    next_protected_boundary: Optional[datetime]
    next_protected_boundary_label: Optional[str]


@dataclass(frozen=True)
class ReconciliationDecision:
    version: str
    reconciliation_days: int
    immediate_candidate_opening: date
    delayed_candidate_opening: date
    immediate_target_date: date
    delayed_target_date: date
    immediate_error_seconds: float
    delayed_error_seconds: float
    operator: str
    reason_code: str = "UNSPECIFIED"
    evidence_source_id: Optional[str] = None
    evidence_sha256: Optional[str] = None
    evidence_event: Optional[str] = None
    evidence_year: Optional[int] = None
    evidence_instant_utc: Optional[datetime] = None

    @property
    def legacy_elapsed_span_days(self) -> int:
        """Elapsed opening-to-opening span. Not a v3.3 ordinary-year length."""
        return 364 + self.reconciliation_days

    @property
    def selected_candidate_opening(self) -> date:
        return (
            self.immediate_candidate_opening
            if self.reconciliation_days == 0
            else self.delayed_candidate_opening
        )

    @property
    def selected_target_date(self) -> date:
        return (
            self.immediate_target_date
            if self.reconciliation_days == 0
            else self.delayed_target_date
        )

    @property
    def selected_error_seconds(self) -> float:
        return (
            self.immediate_error_seconds
            if self.reconciliation_days == 0
            else self.delayed_error_seconds
        )


@dataclass(frozen=True)
class JubileeState:
    cycle: int
    cycle_year: int
    seven_year_block: Optional[int]
    year_within_block: Optional[int]
    is_sabbatical_threshold: bool
    is_jubilee_year: bool


@dataclass(frozen=True)
class DualStamp:
    instant_utc: datetime
    civil_timestamp: datetime
    common_standard_timestamp: datetime
    continuous_k: int
    state: str
    common_date: Optional[CommonDate]
    reconciliation_day: Optional[int]
    reconciliation_address: Optional[str]


@dataclass(frozen=True)
class CalendarSnapshot:
    instant_utc: datetime
    civil_timestamp: datetime
    common_standard_timestamp: datetime
    local_sunset_previous: datetime
    local_sunset_next: datetime
    continuous_k: int
    state: str
    common_date: Optional[CommonDate]
    reconciliation_day: Optional[int]
    reconciliation_address: Optional[str]
    named_day: str
    sabbath_active: bool
    lords_day_active: bool
    stillpoint_active: bool
    next_protected_boundary: Optional[datetime]
    next_protected_boundary_label: Optional[str]
    annual_phase: Optional[int]
    solar_gate: Optional[int]
    jubilee: Optional[JubileeState]
    reference_rule_version: str
    reference_station_id: Optional[str]
    ephemeris_id: Optional[str]
