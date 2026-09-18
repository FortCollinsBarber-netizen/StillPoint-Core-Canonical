from __future__ import annotations

from datetime import date, datetime, timedelta

from .models import GeoPoint, ReconciliationDecision
from .sunset import apparent_sunset_utc

BASE_YEAR_DAYS = 364
SPRING_GATE_ORDINAL = 80


def _error_seconds(boundary: datetime, anchor: datetime) -> float:
    if anchor.tzinfo is None:
        raise ValueError("astronomical anchor must be timezone-aware")
    return abs((boundary - anchor.astimezone(boundary.tzinfo)).total_seconds())


def select_v32_nearest_legal(
    *,
    current_opening: date,
    next_march_equinox: datetime,
    reference_point: GeoPoint,
) -> ReconciliationDecision:
    """Preserve recovered v3.2 semantics as an explicit historical engine."""
    immediate = current_opening + timedelta(days=364)
    delayed = current_opening + timedelta(days=371)
    immediate_boundary = apparent_sunset_utc(immediate, reference_point)
    delayed_boundary = apparent_sunset_utc(delayed, reference_point)

    e0 = _error_seconds(immediate_boundary, next_march_equinox)
    e7 = _error_seconds(delayed_boundary, next_march_equinox)
    reconciliation = 0 if e0 <= e7 else 7

    return ReconciliationDecision(
        version="v3.2",
        reconciliation_days=reconciliation,
        immediate_candidate_opening=immediate,
        delayed_candidate_opening=delayed,
        immediate_target_date=immediate,
        delayed_target_date=delayed,
        immediate_error_seconds=e0,
        delayed_error_seconds=e7,
        operator="NearestLegal",
    )


def spring_gate_date(opening: date, ordinal: int = SPRING_GATE_ORDINAL) -> date:
    if not 1 <= ordinal <= 364:
        raise ValueError("Spring Gate ordinal must be within 1..364")
    return opening + timedelta(days=ordinal - 1)


def select_v33_nearest_spring_gate(
    *,
    current_opening: date,
    next_march_equinox: datetime,
    reference_point: GeoPoint,
    spring_gate_ordinal: int = SPRING_GATE_ORDINAL,
) -> ReconciliationDecision:
    """364-day year plus explicit 0/7-day interannual Reconciliation."""
    immediate = current_opening + timedelta(days=364)
    delayed = immediate + timedelta(days=7)

    immediate_target = spring_gate_date(immediate, spring_gate_ordinal)
    delayed_target = spring_gate_date(delayed, spring_gate_ordinal)
    immediate_boundary = apparent_sunset_utc(immediate_target, reference_point)
    delayed_boundary = apparent_sunset_utc(delayed_target, reference_point)

    e0 = _error_seconds(immediate_boundary, next_march_equinox)
    e7 = _error_seconds(delayed_boundary, next_march_equinox)
    reconciliation = 0 if e0 <= e7 else 7

    return ReconciliationDecision(
        version="v3.3-candidate",
        reconciliation_days=reconciliation,
        immediate_candidate_opening=immediate,
        delayed_candidate_opening=delayed,
        immediate_target_date=immediate_target,
        delayed_target_date=delayed_target,
        immediate_error_seconds=e0,
        delayed_error_seconds=e7,
        operator="NearestLegalSpringGate",
    )
