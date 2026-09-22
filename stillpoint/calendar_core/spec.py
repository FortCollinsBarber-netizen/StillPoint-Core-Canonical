from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .calendar import (
    MONTH_LENGTHS,
    QUARTER_LENGTHS,
)
from .models import DuskProtocol

SPEC_VERSION = "stillpoint-calendar-core-spec-v2"

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


class CalendarSpecValidationError(
    ValueError
):
    def __init__(
        self,
        code: str,
        message: str,
    ) -> None:
        super().__init__(message)
        self.code = code


def build_calendar_core_spec(
) -> dict[str, Any]:
    protocol = DuskProtocol()
    return {
        "version": SPEC_VERSION,
        "jurisdiction": {
            "calendarNamespace":
                "stillpoint.calendar_core",
            "authorityNamespace":
                "stillpoint.temporal",
            "translationAuthority":
                "external-finite-evidence-object",
        },
        "enactmentBoundary": {
            "status":
                "annual-law-ratified-epoch-external",
            "requiredForFiniteProjection": [
                "firstOpening",
                "publicationAuthority",
            ],
            "lawDoesNotSupplyEpoch": True,
        },
        "boundary": {
            "protocolId": protocol.id,
            "apparentHorizonZenithDegrees":
                protocol.zenith_degrees,
            "failurePolicy":
                "explicit-no-silent-fallback",
        },
        "ordinaryCalendar": {
            "baseYearDays": 364,
            "weekDays": 7,
            "weeksPerYear": 52,
            "monthLengths":
                list(MONTH_LENGTHS),
            "quarterLengths":
                list(QUARTER_LENGTHS),
            "yearOpening": {
                "month": 1,
                "day": 1,
            },
            "yearClosing": {
                "month": 12,
                "day": 30,
            },
            "hasFebruary29": False,
            "hasDecember31": False,
        },
        "annualTransition": {
            "rule":
                "DAY_364_TO_NEXT_YEAR_DAY_001",
            "interannualDays": 0,
            "reconciliationAllowed": False,
        },
        "witnessPolicy": {
            "astronomy":
                "witness-only-no-grid-mutation",
            "lunar":
                "witness-only-no-grid-mutation",
            "seasonal":
                "witness-only-no-grid-mutation",
            "enochicGates":
                "witness-metadata-no-grid-mutation",
        },
        "historicalModels": {
            "nearestLegalV32":
                "superseded-non-operative",
            "nearestLegalSpringGateV33":
                "superseded-non-operative",
        },
        "invariants": [
            "year-is-always-364",
            "year-is-always-52-weeks",
            "january-1-is-day-001",
            "december-30-is-day-364",
            "december-31-does-not-exist",
            "february-29-does-not-exist",
            "day-364-transitions-directly-to-next-day-001",
            "no-interannual-reconciliation-days",
            "annual-weekday-pattern-repeats-identically",
            "witness-layers-cannot-mutate-calendar-address",
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
            found = (
                _find_prohibited_enactment_key(
                    child,
                    path=f"{path}.{key}",
                )
            )
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = (
                _find_prohibited_enactment_key(
                    child,
                    path=f"{path}[{index}]",
                )
            )
            if found is not None:
                return found
    return None


def validate_calendar_core_spec(
    document: dict[str, Any],
) -> None:
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
            (
                "unsupported Calendar Core "
                f"spec version: {version}"
            ),
        )

    prohibited = (
        _find_prohibited_enactment_key(
            document
        )
    )
    if prohibited is not None:
        key, path = prohibited
        raise CalendarSpecValidationError(
            "SPEC_CONTAINS_ENACTMENT_DATA",
            (
                "Calendar Core law may not "
                f"contain enactment key {key} "
                f"at {path}"
            ),
        )

    expected = build_calendar_core_spec()
    if document != expected:
        raise CalendarSpecValidationError(
            "SPEC_DRIFT",
            (
                "Calendar Core spec does not "
                "exactly match supported law"
            ),
        )


def export_calendar_core_spec(
    path: Path,
) -> None:
    document = build_calendar_core_spec()
    validate_calendar_core_spec(document)
    path.write_text(
        json.dumps(
            document,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
