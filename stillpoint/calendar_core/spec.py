from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .calendar import MONTH_LENGTHS
from .canonical_map import (
    DAY001_WEEKDAY,
    FIRST_OPENING_CIVIL_DATE,
    FIRST_YEAR_LABEL,
    YEAR_COUNT,
)
from .gates import GATE_SEQUENCE, PHASE_LENGTHS
from .models import DuskProtocol
from .observances import ALL_OBSERVANCES

SPEC_VERSION = "stillpoint-calendar-core-spec-v2"

PROHIBITED_ENACTMENT_KEYS = frozenset(
    {
        "authority",
        "ephemerisEvidence",
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


def _observance_document() -> list[dict[str, Any]]:
    return [
        {
            "id": item.id,
            "name": item.name,
            "jurisdiction": item.jurisdiction,
            "month": item.month,
            "day": item.day,
            "endMonth": item.end_month,
            "endDay": item.end_day,
            "assembly": item.assembly,
            "rule": item.rule,
            "sourceRefs": list(item.source_refs),
        }
        for item in ALL_OBSERVANCES
    ]


def build_calendar_core_spec() -> dict[str, Any]:
    protocol = DuskProtocol()
    return {
        "version": SPEC_VERSION,
        "jurisdiction": {
            "calendarNamespace": "stillpoint.calendar_core",
            "authorityNamespace": "stillpoint.temporal",
            "publicationAuthority": "external-finite-evidence-object",
            "astronomyRole": "witness-only-no-grid-authority",
            "lunarRole": "witness-only-no-grid-authority",
        },
        "enactmentBoundary": {
            "status": "annual-cycle-ratified",
            "lawDoesNotSupplyValues": False,
            "requiredForFinitePublication": [
                "referencePoint",
                "publicationAuthority",
            ],
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
            "lastCommonMonth": 12,
            "lastCommonDay": 30,
            "december31Exists": False,
        },
        "canonicalCycle": {
            "firstYearLabel": FIRST_YEAR_LABEL,
            "firstOpeningCivilDate": FIRST_OPENING_CIVIL_DATE.isoformat(),
            "day001Weekday": DAY001_WEEKDAY,
            "yearCount": YEAR_COUNT,
            "totalDays": 364 * YEAR_COUNT,
            "transition": "12-30->next-year-01-01",
        },
        "reconciliation": {
            "allowedDays": [0],
            "namespace": "prohibited",
            "addressPattern": None,
            "inheritsOrdinaryFields": False,
        },
        "gates": {
            "phaseLengths": list(PHASE_LENGTHS),
            "gateSequence": list(GATE_SEQUENCE),
            "pairedGateCount": 6,
            "role": "enochic-seasonal-witness-layer",
        },
        "referenceRules": {
            "v3.2": {
                "operator": "NearestLegal",
                "status": "historical-non-operative",
            },
            "v3.3Candidate": {
                "operator": "NearestLegalSpringGate",
                "springGateOrdinal": 80,
                "springGateMonth": 3,
                "springGateDay": 20,
                "status": "historical-non-operative",
            },
            "operative": {
                "operator": "Fixed364",
                "status": "ratified",
            },
        },
        "observances": _observance_document(),
        "invariants": [
            "common-year-is-exactly-364-days",
            "common-year-is-exactly-52-seven-day-weeks",
            "december-31-does-not-exist",
            "day-364-transitions-directly-to-next-year-day-001",
            "no-reconciliation-days",
            "no-leap-day",
            "astronomy-cannot-move-the-grid",
            "lunar-observation-cannot-move-the-grid",
            "recurring-observances-retain-weekday",
            "fifty-year-map-is-18200-days",
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
