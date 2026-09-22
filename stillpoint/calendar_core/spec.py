from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .calendar import MONTH_LENGTHS
from .gates import GATE_SEQUENCE, PHASE_LENGTHS
from .sunset import DEFAULT_PROTOCOL

SPEC_VERSION = "stillpoint-calendar-core-spec-v1"
SPRING_GATE_ORDINAL_V33_CANDIDATE = 80

ENGINEERING_INVARIANT = (
    "The week governs sequence. The ordinary calendar governs address. "
    "The Sun governs seasonal correction. The Moon and seasons provide evidence. "
    "Publication gives finite civic coordinates. Jubilee governs a larger release "
    "count. None of them owns the others."
)


def build_calendar_core_spec() -> dict[str, Any]:
    """Return stable machine-readable calendar law with no pilot or enactment."""

    return {
        "version": SPEC_VERSION,
        "status": "stable-domain-spec",
        "engineeringInvariant": ENGINEERING_INVARIANT,
        "jurisdiction": {
            "calendarNamespace": "stillpoint.calendar_core",
            "publicationNamespace": "stillpoint.calendar_publication",
            "witnessNamespace": "stillpoint.calendar_witness",
            "authorityNamespace": "stillpoint.temporal",
        },
        "namespaces": {
            "continuous": {
                "symbol": "K",
                "scope": "sequence-only",
                "neverGaps": True,
            },
            "ordinary": {
                "address": "Y_n-001..Y_n-364",
                "owns": [
                    "ordinaryDayOfYear",
                    "month",
                    "quarter",
                    "phase",
                    "gate",
                ],
            },
            "reconciliation": {
                "address": "Y_n/Y_n+1-R1..R7",
                "allowedDays": [0, 7],
                "inheritsOrdinaryAddressFields": False,
            },
        },
        "ordinaryYear": {
            "days": 364,
            "weeks": 52,
            "monthLengths": list(MONTH_LENGTHS),
            "quarterDays": 91,
            "phaseLengths": list(PHASE_LENGTHS),
            "gateSequence": list(GATE_SEQUENCE),
        },
        "weeklyProtectedTime": {
            "sabbath": "Friday apparent sunset -> Saturday apparent sunset",
            "lordsDay": "Saturday apparent sunset -> Sunday apparent sunset",
            "stillPoint": "Friday apparent sunset -> Sunday apparent sunrise",
            "intervalClosure": "half-open",
        },
        "boundaryConvention": {
            "id": DEFAULT_PROTOCOL.id,
            "apparentHorizonZenithDegrees": DEFAULT_PROTOCOL.zenith_degrees,
            "silentFallbackAllowed": False,
        },
        "supportedPublicationRules": {
            "v3.2": {
                "status": "historical-locked",
                "operator": "NearestLegal",
            },
            "v3.3-candidate": {
                "status": "successor-candidate-not-enacted-by-this-spec",
                "operator": "NearestLegalSpringGate",
                "springGate": {
                    "commonMonth": 3,
                    "commonDay": 20,
                    "ordinal": SPRING_GATE_ORDINAL_V33_CANDIDATE,
                },
            },
        },
        "prohibitions": [
            "ordinary_day_of_year_gt_364",
            "ordinary_fields_on_reconciliation",
            "fractional_week_reconciliation",
            "evidence_self_enactment",
            "client_invention_of_publication_authority",
        ],
    }


def export_calendar_core_spec(path: Path) -> None:
    path.write_text(
        json.dumps(build_calendar_core_spec(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
