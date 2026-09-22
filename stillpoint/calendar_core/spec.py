from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .calendar import MONTH_LENGTHS
from .gates import GATE_SEQUENCE, PHASE_LENGTHS
from .models import DuskProtocol
from .reference_rule import SPRING_GATE_ORDINAL

SPEC_VERSION = "stillpoint-calendar-core-spec-v1"


def build_calendar_core_spec() -> dict[str, Any]:
    protocol = DuskProtocol()
    return {
        "version": SPEC_VERSION,
        "jurisdiction": {
            "calendarNamespace": "stillpoint.calendar_core",
            "authorityNamespace": "stillpoint.temporal",
            "publicationAuthority": "external-finite-evidence-object",
        },
        "boundary": {
            "protocolId": protocol.id,
            "apparentHorizonZenithDegrees": protocol.zenith_degrees,
            "failurePolicy": "explicit-no-silent-fallback",
        },
        "ordinaryCalendar": {
            "baseYearDays": 364,
            "weekDays": 7,
            "monthLengths": list(MONTH_LENGTHS),
            "quarterDays": 91,
            "quarters": 4,
        },
        "reconciliation": {
            "allowedDays": [0, 7],
            "namespace": "interannual",
            "addressPattern": "Y_n/Y_n+1-R{day}",
            "inheritsOrdinaryFields": False,
        },
        "gates": {
            "phaseLengths": list(PHASE_LENGTHS),
            "gateSequence": list(GATE_SEQUENCE),
            "pairedGateCount": 6,
        },
        "referenceRules": {
            "v3.2": {"operator": "NearestLegal", "status": "recovered-historical"},
            "v3.3Candidate": {
                "operator": "NearestLegalSpringGate",
                "springGateOrdinal": SPRING_GATE_ORDINAL,
                "springGateMonth": 3,
                "springGateDay": 20,
                "status": "candidate-unratified",
            },
        },
        "invariants": [
            "continuous-time-never-gaps",
            "ordinary-year-is-always-364",
            "reconciliation-is-0-or-7-and-interannual",
            "reconciliation-inherits-no-month-quarter-phase-gate-or-ordinary-day",
            "week-sequence-is-never-broken",
            "missing-required-evidence-fails-closed",
            "publication-is-finite-and-does-not-self-ratify",
        ],
    }


def export_calendar_core_spec(path: Path) -> None:
    path.write_text(
        json.dumps(build_calendar_core_spec(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
