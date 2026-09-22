from __future__ import annotations

from datetime import date, datetime, timedelta

from .astronomy import AstronomyEvidence, AstronomyEvidenceError, AstronomyProvider
from .models import GeoPoint, ReconciliationDecision
from .sunset import apparent_sunset_utc

BASE_YEAR_DAYS = 364
SPRING_GATE_ORDINAL = 80


def _error_seconds(boundary: datetime, anchor: datetime) -> float:
    if anchor.tzinfo is None:
        raise AstronomyEvidenceError(
            "NAIVE_ASTRONOMICAL_INSTANT",
            "astronomical anchor must be timezone-aware",
        )
    return abs(
        (boundary - anchor.astimezone(boundary.tzinfo)).total_seconds()
    )


def _reason_code(immediate_error: float, delayed_error: float) -> str:
    if immediate_error <= delayed_error:
        return "IMMEDIATE_CLOSER_OR_TIE"
    return "RECONCILIATION_WEEK_CLOSER"


def _decision(
    *,
    version: str,
    operator: str,
    current_opening: date,
    immediate_target: date,
    delayed_target: date,
    evidence: AstronomyEvidence,
    reference_point: GeoPoint,
) -> ReconciliationDecision:
    immediate = current_opening + timedelta(days=BASE_YEAR_DAYS)
    delayed = immediate + timedelta(days=7)

    immediate_boundary = apparent_sunset_utc(
        immediate_target,
        reference_point,
    )
    delayed_boundary = apparent_sunset_utc(
        delayed_target,
        reference_point,
    )

    e0 = _error_seconds(
        immediate_boundary,
        evidence.instant_utc,
    )
    e7 = _error_seconds(
        delayed_boundary,
        evidence.instant_utc,
    )
    reconciliation = 0 if e0 <= e7 else 7

    return ReconciliationDecision(
        version=version,
        reconciliation_days=reconciliation,
        immediate_candidate_opening=immediate,
        delayed_candidate_opening=delayed,
        immediate_target_date=immediate_target,
        delayed_target_date=delayed_target,
        immediate_error_seconds=e0,
        delayed_error_seconds=e7,
        operator=operator,
        reason_code=_reason_code(e0, e7),
        evidence_source_id=evidence.source_id,
        evidence_sha256=evidence.evidence_sha256.lower(),
        evidence_event=evidence.event,
        evidence_year=evidence.year,
        evidence_instant_utc=evidence.instant_utc,
    )


def _legacy_evidence(
    *,
    instant: datetime,
    year: int,
    source_id: str,
) -> AstronomyEvidence:
    if instant.tzinfo is None:
        raise AstronomyEvidenceError(
            "NAIVE_ASTRONOMICAL_INSTANT",
            "astronomical anchor must be timezone-aware",
        )
    # Direct-call compatibility remains explicit and deliberately cannot claim
    # external custody. New publication code should use an AstronomyProvider.
    return AstronomyEvidence(
        event="march_equinox",
        year=year,
        instant_utc=instant,
        source_id=source_id,
        evidence_sha256="0" * 64,
    )


def select_v32_nearest_legal(
    *,
    current_opening: date,
    next_march_equinox: datetime,
    reference_point: GeoPoint,
) -> ReconciliationDecision:
    """Preserve recovered v3.2 semantics as an explicit historical engine."""
    evidence = _legacy_evidence(
        instant=next_march_equinox,
        year=current_opening.year + 1,
        source_id="DIRECT_CALL_UNCUSTODIED",
    )
    immediate = current_opening + timedelta(days=BASE_YEAR_DAYS)
    delayed = current_opening + timedelta(days=BASE_YEAR_DAYS + 7)

    return _decision(
        version="v3.2",
        operator="NearestLegal",
        current_opening=current_opening,
        immediate_target=immediate,
        delayed_target=delayed,
        evidence=evidence,
        reference_point=reference_point,
    )


def spring_gate_date(
    opening: date,
    ordinal: int = SPRING_GATE_ORDINAL,
) -> date:
    if not 1 <= ordinal <= BASE_YEAR_DAYS:
        raise ValueError(
            "Spring Gate ordinal must be within 1..364"
        )
    return opening + timedelta(days=ordinal - 1)


def select_v33_nearest_spring_gate(
    *,
    current_opening: date,
    next_march_equinox: datetime,
    reference_point: GeoPoint,
    spring_gate_ordinal: int = SPRING_GATE_ORDINAL,
) -> ReconciliationDecision:
    """Compatibility entry point for explicit direct astronomical evidence."""
    evidence = _legacy_evidence(
        instant=next_march_equinox,
        year=current_opening.year + 1,
        source_id="DIRECT_CALL_UNCUSTODIED",
    )
    return select_v33_nearest_spring_gate_from_evidence(
        current_opening=current_opening,
        evidence=evidence,
        reference_point=reference_point,
        spring_gate_ordinal=spring_gate_ordinal,
    )


def select_v33_nearest_spring_gate_from_evidence(
    *,
    current_opening: date,
    evidence: AstronomyEvidence,
    reference_point: GeoPoint,
    spring_gate_ordinal: int = SPRING_GATE_ORDINAL,
) -> ReconciliationDecision:
    """364-day year plus explicit 0/7 interannual Reconciliation."""
    expected_year = current_opening.year + 1
    if evidence.year != expected_year:
        raise AstronomyEvidenceError(
            "ASTRONOMY_EVIDENCE_YEAR_MISMATCH",
            f"evidence is for {evidence.year}; expected {expected_year}",
        )

    immediate = current_opening + timedelta(days=BASE_YEAR_DAYS)
    delayed = immediate + timedelta(days=7)
    immediate_target = spring_gate_date(
        immediate,
        spring_gate_ordinal,
    )
    delayed_target = spring_gate_date(
        delayed,
        spring_gate_ordinal,
    )

    return _decision(
        version="v3.3-candidate",
        operator="NearestLegalSpringGate",
        current_opening=current_opening,
        immediate_target=immediate_target,
        delayed_target=delayed_target,
        evidence=evidence,
        reference_point=reference_point,
    )


def select_v33_nearest_spring_gate_from_provider(
    *,
    current_opening: date,
    provider: AstronomyProvider,
    reference_point: GeoPoint,
    spring_gate_ordinal: int = SPRING_GATE_ORDINAL,
) -> ReconciliationDecision:
    """Resolve one bounded evidence event, then apply the v3.3 operator."""
    expected_year = current_opening.year + 1
    evidence = provider.march_equinox(expected_year)
    return select_v33_nearest_spring_gate_from_evidence(
        current_opening=current_opening,
        evidence=evidence,
        reference_point=reference_point,
        spring_gate_ordinal=spring_gate_ordinal,
    )
