from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .calendar import MONTH_LENGTHS
from .gates import GATE_SEQUENCE, PHASE_LENGTHS
from .models import DuskProtocol
from .reference_rule import SPRING_GATE_ORDINAL

SPEC_VERSION = "stillpoint-calendar-core-spec-v1"

PROHIBITED_ENACTMENT_KEYS = frozenset(
    {
        "authority",
        "ephemerisEvidence",
        "firstOpening",
        "jubileeEpoch",
        "openingCivilDate",
        "pilotCalibration",
        "publicationDigest",
        "referencePoint",
        "years",
    }
)


class CalendarSpecValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def build_calendar_core_spec() -> dict[str, Any]:
    protocol = DuskProtocol()
    return {
        "version": SPEC_VERSION,
        "jurisdiction": {
            "calendarNamespace": "stillpoint.calendar_core",
            "authorityNamespace": "stillpoint.temporal",
            "publicationAuthority": "external-finite-evidence-object",
        },
        "enactmentBoundary": {
            "status": "external-unresolved",
            "requiredForFinitePublication": [
                "firstOpening",
                "referencePoint",
                "ephemerisEvidence",
                "publicationAuthority",
            ],
            "lawDoesNotSupplyValues": True,
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
            "v3.2": {
                "operator": "NearestLegal",
                "status": "recovered-historical",
            },
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


def _find_prohibited_enactment_key(
    value: Any,
    *,
    path: str = "$",
) -> tuple[str, str] | None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in PROHIBITED_ENACTMENT_KEYS:
                return key, f"{path}.{key}"
            found = _find_prohibited_enactment_key(
                child,
                path=f"{path}.{key}",
            )
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = _find_prohibited_enactment_key(
                child,
                path=f"{path}[{index}]",
            )
            if found is not None:
                return found
    return None


def validate_calendar_core_spec(document: dict[str, Any]) -> None:
    if not isinstance(document, dict):
        raise CalendarSpecValidationError(
            "INVALID_SPEC_DOCUMENT",
            "Calendar Core spec must be a JSON object",
        )

    version = document.get("version")
    if not isinstance(version, str):
        raise CalendarSpecValidationError(
            "MISSING_SPEC_VERSION",
            "Calendar Core spec version is required",
        )
    if version != SPEC_VERSION:
        raise CalendarSpecValidationError(
            "UNSUPPORTED_SPEC_VERSION",
            f"unsupported Calendar Core spec version: {version}",
        )

    prohibited = _find_prohibited_enactment_key(document)
    if prohibited is not None:
        key, path = prohibited
        raise CalendarSpecValidationError(
            "SPEC_CONTAINS_ENACTMENT_DATA",
            f"Calendar Core law may not contain enactment key {key} at {path}",
        )

    expected = build_calendar_core_spec()
    if document != expected:
        raise CalendarSpecValidationError(
            "SPEC_DRIFT",
            "Calendar Core spec does not exactly match the supported law artifact",
        )


def export_calendar_core_spec(path: Path) -> None:
    document = build_calendar_core_spec()
    validate_calendar_core_spec(document)
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
