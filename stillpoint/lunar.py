"""Deterministic lunar phase witness for Clock OS.

This is a mean-lunation witness layer. It reports lunar state for an instant
but has no authority to alter Calendar Core dates, months, feasts, or the
364-day grid. Observational evidence may supersede this calculated witness
without rewriting calendar law.
"""

from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any


LUNAR_SCHEMA = "stillpoint.lunar-witness.v1"
SYNODIC_MONTH_DAYS = 29.530588853
REFERENCE_NEW_MOON = datetime.fromtimestamp(947_182_440, tz=timezone.utc)


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


def lunar_phase_witness(instant: datetime) -> dict[str, Any]:
    if instant.tzinfo is None:
        raise ValueError("instant must be timezone-aware")

    instant_utc = instant.astimezone(timezone.utc)
    elapsed_days = (
        instant_utc - REFERENCE_NEW_MOON
    ).total_seconds() / 86_400.0
    age = elapsed_days % SYNODIC_MONTH_DAYS
    angle = 2.0 * math.pi * (age / SYNODIC_MONTH_DAYS)
    illumination = 0.5 * (1.0 - math.cos(angle))
    waxing = age < SYNODIC_MONTH_DAYS / 2.0

    return {
        "schema": LUNAR_SCHEMA,
        "model": "mean-lunation-v1",
        "reference_new_moon_utc": REFERENCE_NEW_MOON.isoformat(),
        "synodic_month_days": SYNODIC_MONTH_DAYS,
        "age_days": age,
        "illumination_fraction": illumination,
        "illumination_percent": int(round(illumination * 100.0)),
        "is_waxing": waxing,
        "phase_name": _phase_name(age),
        "evidence_label": "MEAN LUNATION · WITNESS ONLY",
        "calendar_effect": "none",
    }
