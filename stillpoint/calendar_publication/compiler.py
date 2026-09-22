from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta
from typing import Any, Mapping

from stillpoint.calendar_core.models import GeoPoint, ReconciliationDecision
from stillpoint.calendar_core.sunset import apparent_sunset_utc

PUBLICATION_VERSION = "stillpoint-calendar-publication-v1"
SPRING_GATE_ORDINAL_V33 = 80
BASE_YEAR_DAYS = 364
ALLOWED_AUTHORITY_STATUSES = {"CONFORMANCE", "PILOT", "RATIFIED"}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _error_seconds(boundary: datetime, anchor: datetime) -> float:
    if anchor.tzinfo is None:
        raise ValueError("astronomical anchor must be timezone-aware")
    return abs((boundary - anchor.astimezone(boundary.tzinfo)).total_seconds())


def spring_gate_date(
    opening: date,
    ordinal: int = SPRING_GATE_ORDINAL_V33,
) -> date:
    if not 1 <= ordinal <= BASE_YEAR_DAYS:
        raise ValueError("Spring Gate ordinal must be within 1..364")
    return opening + timedelta(days=ordinal - 1)


def select_v32_nearest_legal(
    *,
    current_opening: date,
    next_march_equinox: datetime,
    reference_point: GeoPoint,
) -> ReconciliationDecision:
    """Historical v3.2 rule. Kept versioned; never selected implicitly."""

    immediate = current_opening + timedelta(days=364)
    delayed = current_opening + timedelta(days=371)
    immediate_boundary = apparent_sunset_utc(immediate, reference_point)
    delayed_boundary = apparent_sunset_utc(delayed, reference_point)

    e0 = _error_seconds(immediate_boundary, next_march_equinox)
    e7 = _error_seconds(delayed_boundary, next_march_equinox)

    return ReconciliationDecision(
        version="v3.2",
        reconciliation_days=0 if e0 <= e7 else 7,
        immediate_candidate_opening=immediate,
        delayed_candidate_opening=delayed,
        immediate_target_date=immediate,
        delayed_target_date=delayed,
        immediate_error_seconds=e0,
        delayed_error_seconds=e7,
        operator="NearestLegal",
    )


def select_v33_nearest_spring_gate(
    *,
    current_opening: date,
    next_march_equinox: datetime,
    reference_point: GeoPoint,
    spring_gate_ordinal: int = SPRING_GATE_ORDINAL_V33,
) -> ReconciliationDecision:
    """Select 0/7 re-entry; evidence chooses between lawful candidates only."""

    immediate = current_opening + timedelta(days=BASE_YEAR_DAYS)
    delayed = immediate + timedelta(days=7)

    immediate_target = spring_gate_date(immediate, spring_gate_ordinal)
    delayed_target = spring_gate_date(delayed, spring_gate_ordinal)
    immediate_boundary = apparent_sunset_utc(immediate_target, reference_point)
    delayed_boundary = apparent_sunset_utc(delayed_target, reference_point)

    e0 = _error_seconds(immediate_boundary, next_march_equinox)
    e7 = _error_seconds(delayed_boundary, next_march_equinox)

    return ReconciliationDecision(
        version="v3.3-candidate",
        reconciliation_days=0 if e0 <= e7 else 7,
        immediate_candidate_opening=immediate,
        delayed_candidate_opening=delayed,
        immediate_target_date=immediate_target,
        delayed_target_date=delayed_target,
        immediate_error_seconds=e0,
        delayed_error_seconds=e7,
        operator="NearestLegalSpringGate",
    )


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def publication_digest(document: dict[str, Any]) -> str:
    unsigned = {
        key: value
        for key, value in document.items()
        if key != "publicationDigest"
    }
    return sha256_bytes(canonical_bytes(unsigned))


def compile_v33_publication(
    *,
    publication_id: str,
    authority_status: str,
    authority_id: str,
    reference_point: GeoPoint,
    reference_point_id: str,
    reference_geometry_digest: str,
    first_year_label: int,
    first_opening: date,
    first_opening_continuous_k: int,
    day001_weekday: str,
    count: int,
    march_equinoxes: Mapping[int, datetime],
    evidence_source_id: str,
    evidence_digest: str,
) -> dict[str, Any]:
    """Compile finite civic coordinates from explicit authority + evidence.

    Astronomical evidence cannot enact itself: authority_status, authority_id,
    reference identity, epoch, and evidence binding are all required inputs.
    """

    if authority_status not in ALLOWED_AUTHORITY_STATUSES:
        raise ValueError("unsupported authority_status")
    if not publication_id or not authority_id or not reference_point_id:
        raise ValueError("publication, authority, and reference identifiers are required")
    if not _SHA256.fullmatch(reference_geometry_digest):
        raise ValueError("reference_geometry_digest must be lowercase SHA-256")
    if not _SHA256.fullmatch(evidence_digest):
        raise ValueError("evidence_digest must be lowercase SHA-256")
    if not evidence_source_id:
        raise ValueError("evidence_source_id is required")
    if first_opening_continuous_k < 0:
        raise ValueError("first_opening_continuous_k must be >= 0")
    if count < 1:
        raise ValueError("count must be >= 1")

    rows: list[dict[str, Any]] = []
    opening = first_opening
    opening_k = first_opening_continuous_k

    for offset in range(count):
        year = first_year_label + offset
        evidence_year = year + 1
        equinox = march_equinoxes.get(evidence_year)
        if equinox is None:
            raise ValueError(
                f"EPHEMERIS_UNAVAILABLE: missing March equinox evidence for {evidence_year}"
            )
        if equinox.tzinfo is None:
            raise ValueError("ephemeris instants must be timezone-aware")

        decision = select_v33_nearest_spring_gate(
            current_opening=opening,
            next_march_equinox=equinox,
            reference_point=reference_point,
        )
        next_k = opening_k + BASE_YEAR_DAYS + decision.reconciliation_days

        rows.append(
            {
                "year": year,
                "openingCivilDate": opening.isoformat(),
                "openingContinuousK": opening_k,
                "ordinaryDays": BASE_YEAR_DAYS,
                "reconciliationDaysAfterCompletion": decision.reconciliation_days,
                "nextOpeningCivilDate": decision.immediate_candidate_opening.isoformat()
                if decision.reconciliation_days == 0
                else decision.delayed_candidate_opening.isoformat(),
                "nextOpeningContinuousK": next_k,
                "governingMarchEquinoxUTC": (
                    equinox.isoformat().replace("+00:00", "Z")
                ),
                "immediateSpringGateCivilDate": decision.immediate_target_date.isoformat(),
                "delayedSpringGateCivilDate": decision.delayed_target_date.isoformat(),
                "immediateErrorSeconds": decision.immediate_error_seconds,
                "delayedErrorSeconds": decision.delayed_error_seconds,
            }
        )

        opening = (
            decision.immediate_candidate_opening
            if decision.reconciliation_days == 0
            else decision.delayed_candidate_opening
        )
        opening_k = next_k

    final_exclusive = opening.isoformat()
    document: dict[str, Any] = {
        "version": PUBLICATION_VERSION,
        "publicationId": publication_id,
        "authority": {
            "status": authority_status,
            "authorityId": authority_id,
        },
        "rule": {
            "version": "v3.3-candidate",
            "operator": "NearestLegalSpringGate",
            "springGateOrdinal": SPRING_GATE_ORDINAL_V33,
        },
        "referencePoint": {
            "id": reference_point_id,
            "geometryDigest": reference_geometry_digest,
        },
        "evidence": {
            "sourceId": evidence_source_id,
            "sha256": evidence_digest,
        },
        "epoch": {
            "firstYearLabel": first_year_label,
            "firstOpeningCivilDate": first_opening.isoformat(),
            "firstOpeningContinuousK": first_opening_continuous_k,
            "day001Weekday": day001_weekday,
        },
        "effectiveRange": {
            "firstOpeningCivilDate": first_opening.isoformat(),
            "finalExclusiveOpeningCivilDate": final_exclusive,
            "yearCount": count,
        },
        "years": rows,
    }
    document["publicationDigest"] = publication_digest(document)
    validate_calendar_publication(document)
    return document


def validate_calendar_publication(document: dict[str, Any]) -> None:
    if document.get("version") != PUBLICATION_VERSION:
        raise ValueError("unsupported publication version")
    supplied = document.get("publicationDigest")
    if not isinstance(supplied, str) or supplied != publication_digest(document):
        raise ValueError("publication digest mismatch")

    authority = document.get("authority", {})
    if authority.get("status") not in ALLOWED_AUTHORITY_STATUSES:
        raise ValueError("invalid authority status")

    rows = document.get("years")
    if not isinstance(rows, list) or not rows:
        raise ValueError("publication must contain a finite non-empty year table")

    for index, row in enumerate(rows):
        if row.get("ordinaryDays") != BASE_YEAR_DAYS:
            raise ValueError("ordinary year must remain 364 days")
        reconciliation = row.get("reconciliationDaysAfterCompletion")
        if reconciliation not in (0, 7):
            raise ValueError("reconciliation must be 0 or 7 days")
        if row.get("nextOpeningContinuousK") - row.get("openingContinuousK") != (
            BASE_YEAR_DAYS + reconciliation
        ):
            raise ValueError("continuous K span mismatch")
        if index + 1 < len(rows):
            nxt = rows[index + 1]
            if nxt.get("openingCivilDate") != row.get("nextOpeningCivilDate"):
                raise ValueError("civil opening chain mismatch")
            if nxt.get("openingContinuousK") != row.get("nextOpeningContinuousK"):
                raise ValueError("continuous K chain mismatch")
