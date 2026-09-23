from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .calendar import DAY001_WEEKDAY, MONTH_LENGTHS
from .gates import GATE_SEQUENCE, PHASE_LENGTHS
from .models import DuskProtocol

SPEC_VERSION = "stillpoint-calendar-core-spec-v2-fixed-364"

PROHIBITED_ENACTMENT_KEYS = frozenset(
    {
        "ephemerisEvidence",
        "openingCivilDate",
        "pilotCalibration",
        "publicationDigest",
        "referencePoint",
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
            "primary": "fixed-364-day-sacred-civic-grid",
            "calendarNamespace": "stillpoint.calendar_core",
            "authorityNamespace": "stillpoint.temporal",
            "astronomyRole": "witness-and-boundary-evidence-not-grid-authority",
            "civilCalendarRole": "translation-layer-not-grid-authority",
        },
        "grid": {
            "status": "ratified-fixed",
            "days": 364,
            "weeks": 52,
            "day001Weekday": DAY001_WEEKDAY,
            "firstDate": {"month": 1, "day": 1},
            "lastDate": {"month": 12, "day": 30},
            "december31Exists": False,
            "nextAfterLastDate": {"month": 1, "day": 1},
            "interannualDays": 0,
        },
        "boundary": {
            "protocolId": protocol.id,
            "apparentHorizonZenithDegrees": protocol.zenith_degrees,
            "role": "local-day-boundary-only",
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
            "enabled": False,
            "allowedDays": [0],
            "namespace": "abolished",
            "addressPattern": "none",
            "inheritsOrdinaryFields": False,
        },
        "enochicArchitecture": {
            "phaseLengths": list(PHASE_LENGTHS),
            "gateSequence": list(GATE_SEQUENCE),
            "pairedGateCount": 6,
            "quarterDays": 91,
            "quarters": 4,
            "role": "ordinal-sacred-geometry",
        },
        "historicalReferenceRules": {
            "v3.2": {
                "operator": "NearestLegal",
                "status": "historical-superseded",
            },
            "v3.3": {
                "operator": "NearestLegalSpringGate",
                "status": "historical-superseded",
            },
        },
        "invariants": [
            "day-001-through-day-364-only",
            "december-31-does-not-exist",
            "day-364-transitions-directly-to-next-year-day-001",
            "every-year-is-exactly-52-weeks",
            "weekday-addresses-repeat-identically-every-year",
            "astronomy-may-witness-but-cannot-move-the-grid",
            "lunar-evidence-may-witness-but-cannot-move-the-grid",
            "civil-translation-may-describe-but-cannot-move-the-grid",
            "jubilee-counts-years-but-cannot-move-the-grid",
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
            "SPEC_CONTAINS_EXTERNAL_EVIDENCE",
            f"Calendar Core law may not contain external evidence key {key} at {path}",
        )
    expected = build_calendar_core_spec()
    if document != expected:
        raise CalendarSpecValidationError(
            "SPEC_DRIFT",
            "Calendar Core spec does not exactly match the supported fixed-grid law",
        )


def export_calendar_core_spec(path: Path) -> None:
    document = build_calendar_core_spec()
    validate_calendar_core_spec(document)
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
