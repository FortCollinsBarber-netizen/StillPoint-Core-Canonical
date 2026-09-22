from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import hashlib
import json
from typing import Any, Collection, Sequence

from .spec import SPEC_VERSION

BASE_YEAR_DAYS = 364
ALLOWED_RECONCILIATION_DAYS = (0, 7)
PUBLICATION_VERSION = "stillpoint-calendar-publication-v1"
ALLOWED_AUTHORITY_STATUSES = ("pilot", "enacted")


class PublicationValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class PublicationRange:
    first_opening: date
    expires_at_opening: date
    year_count: int


@dataclass(frozen=True)
class PublicationEnvelope:
    publication_version: str
    calendar_core_spec_version: str
    authority_id: str
    authority_status: str
    reference_rule_version: str
    reference_station_id: str
    ephemeris_id: str
    ephemeris_sha256: str
    publication_range: PublicationRange
    publication_digest: str


def canonical_publication_bytes(document: dict[str, Any]) -> bytes:
    payload = {
        key: value
        for key, value in document.items()
        if key != "publicationDigest"
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def publication_digest(document: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_publication_bytes(document)).hexdigest()


def _nonempty_string(
    container: dict[str, Any],
    key: str,
    *,
    code: str,
) -> str:
    value = container.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PublicationValidationError(
            code,
            f"{key} must be a non-empty string",
        )
    return value.strip()


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in value)


def validate_publication_rows(rows: Sequence[dict[str, Any]]) -> PublicationRange:
    if not rows:
        raise PublicationValidationError(
            "EMPTY_PUBLICATION",
            "publication must contain at least one year row",
        )

    parsed: list[tuple[date, int, int]] = []
    seen_years: set[int] = set()

    for row in rows:
        try:
            year = int(row["year"])
            opening = date.fromisoformat(str(row["openingCivilDate"]))
            reconciliation = int(row["reconciliationDaysAfterCompletion"])
        except (KeyError, TypeError, ValueError) as exc:
            raise PublicationValidationError(
                "INVALID_PUBLICATION_ROW",
                "publication row is missing a valid year/opening/reconciliation",
            ) from exc

        if year in seen_years:
            raise PublicationValidationError(
                "DUPLICATE_PUBLICATION_YEAR",
                f"publication contains duplicate year {year}",
            )
        seen_years.add(year)

        if reconciliation not in ALLOWED_RECONCILIATION_DAYS:
            raise PublicationValidationError(
                "INVALID_RECONCILIATION",
                "reconciliation must be exactly 0 or 7 days",
            )

        parsed.append((opening, reconciliation, year))

    if parsed != sorted(parsed, key=lambda item: item[0]):
        raise PublicationValidationError(
            "UNSORTED_PUBLICATION",
            "publication rows must be ordered by opening",
        )

    for index in range(len(parsed) - 1):
        opening, reconciliation, year = parsed[index]
        next_opening, _, next_year = parsed[index + 1]

        if next_year != year + 1:
            raise PublicationValidationError(
                "NONCONTIGUOUS_PUBLICATION_YEARS",
                f"year {year} is followed by {next_year}",
            )

        expected = BASE_YEAR_DAYS + reconciliation
        actual = (next_opening - opening).days
        if actual != expected:
            raise PublicationValidationError(
                "OPENING_SPAN_MISMATCH",
                f"year {year} declares {expected} opening-to-opening days; got {actual}",
            )

    last_opening, last_reconciliation, _ = parsed[-1]
    return PublicationRange(
        first_opening=parsed[0][0],
        expires_at_opening=last_opening
        + timedelta(days=BASE_YEAR_DAYS + last_reconciliation),
        year_count=len(parsed),
    )


def validate_publication_document(
    document: dict[str, Any],
    *,
    expected_spec_version: str = SPEC_VERSION,
    authorized_authority_ids: Collection[str] | None = None,
    require_authority_status: str | None = None,
    expected_reference_rule_version: str | None = None,
    expected_reference_station_id: str | None = None,
    expected_ephemeris_id: str | None = None,
    expected_ephemeris_sha256: str | None = None,
    superseded_publication_digests: Collection[str] | None = None,
    at_opening: date | None = None,
) -> PublicationEnvelope:
    if not isinstance(document, dict):
        raise PublicationValidationError(
            "INVALID_PUBLICATION_DOCUMENT",
            "publication must be a JSON object",
        )

    supplied_digest = document.get("publicationDigest")
    if not isinstance(supplied_digest, str) or not _valid_sha256(supplied_digest):
        raise PublicationValidationError(
            "INVALID_PUBLICATION_DIGEST",
            "publicationDigest must be a SHA-256 hex digest",
        )

    expected_digest = publication_digest(document)
    if supplied_digest.lower() != expected_digest:
        raise PublicationValidationError(
            "PUBLICATION_DIGEST_MISMATCH",
            "publication content does not match publicationDigest",
        )

    normalized_digest = supplied_digest.lower()
    if superseded_publication_digests is not None:
        superseded = {value.lower() for value in superseded_publication_digests}
        if normalized_digest in superseded:
            raise PublicationValidationError(
                "PUBLICATION_SUPERSEDED",
                "publication remains historical evidence but no longer has operative authority",
            )

    publication_version = _nonempty_string(
        document,
        "publicationVersion",
        code="MISSING_PUBLICATION_VERSION",
    )
    if publication_version != PUBLICATION_VERSION:
        raise PublicationValidationError(
            "UNSUPPORTED_PUBLICATION_VERSION",
            f"unsupported publication version: {publication_version}",
        )

    spec_version = _nonempty_string(
        document,
        "calendarCoreSpecVersion",
        code="MISSING_CALENDAR_SPEC_VERSION",
    )
    if spec_version != expected_spec_version:
        raise PublicationValidationError(
            "UNSUPPORTED_CALENDAR_SPEC_VERSION",
            f"publication uses {spec_version}; expected {expected_spec_version}",
        )

    authority = document.get("authority")
    if not isinstance(authority, dict):
        raise PublicationValidationError(
            "MISSING_PUBLICATION_AUTHORITY",
            "publication.authority must be an object",
        )

    authority_id = _nonempty_string(
        authority,
        "id",
        code="MISSING_PUBLICATION_AUTHORITY",
    )
    authority_status = _nonempty_string(
        authority,
        "status",
        code="MISSING_PUBLICATION_AUTHORITY",
    )

    if authority_status not in ALLOWED_AUTHORITY_STATUSES:
        raise PublicationValidationError(
            "INVALID_AUTHORITY_STATUS",
            f"authority status must be one of {ALLOWED_AUTHORITY_STATUSES}",
        )

    if (
        authorized_authority_ids is not None
        and authority_id not in set(authorized_authority_ids)
    ):
        raise PublicationValidationError(
            "UNAUTHORIZED_PUBLICATION_AUTHORITY",
            f"authority {authority_id} is not authorized for this projection",
        )

    if (
        require_authority_status is not None
        and authority_status != require_authority_status
    ):
        raise PublicationValidationError(
            "PUBLICATION_AUTHORITY_STATUS_MISMATCH",
            f"publication authority is {authority_status}; required {require_authority_status}",
        )

    reference_rule_version = _nonempty_string(
        document,
        "referenceRuleVersion",
        code="MISSING_REFERENCE_RULE_VERSION",
    )
    if (
        expected_reference_rule_version is not None
        and reference_rule_version != expected_reference_rule_version
    ):
        raise PublicationValidationError(
            "REFERENCE_RULE_MISMATCH",
            f"publication uses {reference_rule_version}; expected {expected_reference_rule_version}",
        )

    reference_point = document.get("referencePoint")
    if not isinstance(reference_point, dict):
        raise PublicationValidationError(
            "MISSING_REFERENCE_POINT",
            "publication.referencePoint must be an object",
        )

    reference_station_id = _nonempty_string(
        reference_point,
        "id",
        code="MISSING_REFERENCE_POINT",
    )
    if (
        expected_reference_station_id is not None
        and reference_station_id != expected_reference_station_id
    ):
        raise PublicationValidationError(
            "REFERENCE_POINT_MISMATCH",
            f"publication uses reference {reference_station_id}; expected {expected_reference_station_id}",
        )

    ephemeris = document.get("ephemerisEvidence")
    if not isinstance(ephemeris, dict):
        raise PublicationValidationError(
            "MISSING_EPHEMERIS_EVIDENCE",
            "publication.ephemerisEvidence must be an object",
        )

    ephemeris_id = _nonempty_string(
        ephemeris,
        "source",
        code="MISSING_EPHEMERIS_EVIDENCE",
    )
    if expected_ephemeris_id is not None and ephemeris_id != expected_ephemeris_id:
        raise PublicationValidationError(
            "EPHEMERIS_SOURCE_MISMATCH",
            f"publication uses ephemeris {ephemeris_id}; expected {expected_ephemeris_id}",
        )

    ephemeris_sha256 = _nonempty_string(
        ephemeris,
        "sha256",
        code="MISSING_EPHEMERIS_EVIDENCE",
    )
    if not _valid_sha256(ephemeris_sha256):
        raise PublicationValidationError(
            "INVALID_EPHEMERIS_DIGEST",
            "ephemerisEvidence.sha256 must be a SHA-256 hex digest",
        )
    if (
        expected_ephemeris_sha256 is not None
        and ephemeris_sha256.lower() != expected_ephemeris_sha256.lower()
    ):
        raise PublicationValidationError(
            "EPHEMERIS_DIGEST_MISMATCH",
            "publication ephemeris digest does not match required evidence",
        )

    rows = document.get("years")
    if not isinstance(rows, list):
        raise PublicationValidationError(
            "INVALID_PUBLICATION_ROWS",
            "publication.years must be an array",
        )

    publication_range = validate_publication_rows(rows)

    if at_opening is not None:
        if at_opening < publication_range.first_opening:
            raise PublicationValidationError(
                "PUBLICATION_NOT_YET_EFFECTIVE",
                "requested opening predates this publication's finite authority",
            )
        if at_opening >= publication_range.expires_at_opening:
            raise PublicationValidationError(
                "PUBLICATION_EXPIRED",
                "publication remains historical evidence but its operative range has ended",
            )

    return PublicationEnvelope(
        publication_version=publication_version,
        calendar_core_spec_version=spec_version,
        authority_id=authority_id,
        authority_status=authority_status,
        reference_rule_version=reference_rule_version,
        reference_station_id=reference_station_id,
        ephemeris_id=ephemeris_id,
        ephemeris_sha256=ephemeris_sha256.lower(),
        publication_range=publication_range,
        publication_digest=normalized_digest,
    )
