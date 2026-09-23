from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math

SYNODIC_MONTH_DAYS = 29.530588853
REFERENCE_NEW_MOON_UTC = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)


@dataclass(frozen=True)
class LunarPhaseState:
    age_days: float
    illumination_fraction: float
    is_waxing: bool
    phase_name: str
    evidence_label: str = "mean-lunation-witness-only"

    @property
    def illumination_percent(self) -> int:
        return round(self.illumination_fraction * 100.0)


def _phase_name(age_days: float) -> str:
    eighth = SYNODIC_MONTH_DAYS / 8.0
    if age_days < eighth / 2.0:
        return "NEW MOON"
    if age_days < eighth * 1.5:
        return "WAXING CRESCENT"
    if age_days < eighth * 2.5:
        return "FIRST QUARTER"
    if age_days < eighth * 3.5:
        return "WAXING GIBBOUS"
    if age_days < eighth * 4.5:
        return "FULL MOON"
    if age_days < eighth * 5.5:
        return "WANING GIBBOUS"
    if age_days < eighth * 6.5:
        return "LAST QUARTER"
    if age_days < eighth * 7.5:
        return "WANING CRESCENT"
    return "NEW MOON"


def lunar_phase_state(instant: datetime) -> LunarPhaseState:
    if instant.tzinfo is None:
        raise ValueError("instant must be timezone-aware")
    elapsed_days = (
        instant.astimezone(timezone.utc) - REFERENCE_NEW_MOON_UTC
    ).total_seconds() / 86_400.0
    age = elapsed_days % SYNODIC_MONTH_DAYS
    angle = 2.0 * math.pi * (age / SYNODIC_MONTH_DAYS)
    illumination = 0.5 * (1.0 - math.cos(angle))
    return LunarPhaseState(
        age_days=age,
        illumination_fraction=illumination,
        is_waxing=age < SYNODIC_MONTH_DAYS / 2.0,
        phase_name=_phase_name(age),
    )
