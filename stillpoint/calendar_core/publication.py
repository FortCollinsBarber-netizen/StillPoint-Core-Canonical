from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import hashlib
import json
from typing import Any, Collection, Sequence

from .spec import SPEC_VERSION

BASE_YEAR_DAYS = 364
PUBLICATION_VERSION = "stillpoint-calendar-publication-v2"
ALLOWED_AUTHORITY_STATUSES = ("pilot", "enacted")
PROJECTION_SEMANTICS = {
    "openingCivilDate": {
        "frame": "proleptic-gregorian",
        "role": "external-translation-only",
        "gridAuthority": False,
    },
    "commonYear": {
        "opening": {"month": 1, "day": 1},
        "closing": {"month": 12, "day": 30},
        "dateLabels": "canonical-common-calendar",
    },
}
FORBIDDEN_SUPERSEDED_ROW_KEYS = frozenset({
    "reconciliationDaysAfterCompletion",
    "reconciliationReasonCode",
    "governingMarchEquinoxYear",
    "governingMarchEquinoxUTC",
    "immediateCandidateOpeningCivilDate",
    "delayedCandidateOpeningCivilDate",
    "immediateSpringGateCivilDate",
    "delayedSpringGateCivilDate",
    "immediateErrorSeconds",
    "delayedErrorSeconds",
    "nextYearSpringGateCivilDate",
})


class PublicationValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class PublicationRange:
    first_opening: date
    expires_at_opening: date
    first_year: int
    last_year: int
    year_count: int


@dataclass(frozen=True)
class PublicationEnvelope:
    publication_version: str
    calendar_core_spec_version: str
    authority_id: str
    authority_status: str
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
    return hashlib.sha256(
        canonical_publication_bytes(document)
    ).hexdigest()


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
    return (
        len(value) == 64
        and all(ch in "0123456789abcdefABCDEF" for ch in value)
    )


def validate_publication_rows(
    rows: Sequence[dict[str, Any]],
) -> PublicationRange:
    if not rows:
        raise PublicationValidationError(
            "EMPTY_PUBLICATION",
            "publication must contain at least one year row",
        )

    parsed: list[tuple[date, int]] = []
    seen_years: set[int] = set()

    for row in rows:
        if not isinstance(row, dict):
            raise PublicationValidationError(
                "INVALID_PUBLICATION_ROW",
                "each publication year row must be an object",
            )

        forbidden = FORBIDDEN_SUPERSEDED_ROW_KEYS.intersection(row)
        if forbidden:
            raise PublicationValidationError(
                "SUPERSEDED_RECONCILIATION_FIELD",
                "immutable v2 publication may not contain: "
                + ", ".join(sorted(forbidden)),
            )

        try:
            year = int(row["year"])
            opening = date.fromisoformat(
                str(row["openingCivilDate"])
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise PublicationValidationError(
                "INVALID_PUBLICATION_ROW",
                "publication row requires valid year and openingCivilDate",
            ) from exc

        allowed = {"year", "openingCivilDate"}
        extra = set(row) - allowed
        if extra:
            raise PublicationValidationError(
                "UNSUPPORTED_PUBLICATION_ROW_FIELD",
                "unsupported year-row fields: "
                + ", ".join(sorted(extra)),
            )

        if year in seen_years:
            raise PublicationValidationError(
                "DUPLICATE_PUBLICATION_YEAR",
                f"publication contains duplicate year {year}",
            )
        seen_years.add(year)
        parsed.append((opening, year))

    if parsed != sorted(parsed, key=lambda item: item[0]):
        raise PublicationValidationError(
            "UNSORTED_PUBLICATION",
            "publication rows must be ordered by opening",
        )

    for index in range(len(parsed) - 1):
        opening, year = parsed[index]
        next_opening, next_year = parsed[index + 1]

        if next_year != year + 1:
            raise PublicationValidationError(
                "NONCONTIGUOUS_PUBLICATION_YEARS",
                f"year {year} is followed by {next_year}",
            )

        actual = (next_opening - opening).days
        if actual != BASE_YEAR_DAYS:
            raise PublicationValidationError(
                "OPENING_SPAN_MISMATCH",
                f"year {year} must span exactly 364 days; got {actual}",
            )

    first_opening, first_year = parsed[0]
    last_opening, last_year = parsed[-1]
    return PublicationRange(
        first_opening=first_opening,
        expires_at_opening=last_opening + timedelta(days=BASE_YEAR_DAYS),
        first_year=first_year,
        last_year=last_year,
        year_count=len(parsed),
    )


def validate_publication_document(
    document: dict[str, Any],
    *,
    expected_spec_version: str = SPEC_VERSION,
    authorized_authority_ids: Collection[str] | None = None,
    require_authority_status: str | None = None,
    expected_first_opening: date | None = None,
    expected_first_year: int | None = None,
    superseded_publication_digests: Collection[str] | None = None,
    at_opening: date | None = None,
) -> PublicationEnvelope:
    if not isinstance(document, dict):
        raise PublicationValidationError(
            "INVALID_PUBLICATION_DOCUMENT",
            "publication must be a JSON object",
        )

    allowed_top = {
        "publicationVersion",
        "calendarCoreSpecVersion",
        "authority",
        "projectionSemantics",
        "years",
        "publicationDigest",
    }
    extra_top = set(document) - allowed_top
    if extra_top:
        raise PublicationValidationError(
            "UNSUPPORTED_PUBLICATION_FIELD",
            "unsupported publication fields: "
            + ", ".join(sorted(extra_top)),
        )

    supplied_digest = document.get("publicationDigest")
    if (
        not isinstance(supplied_digest, str)
        or not _valid_sha256(supplied_digest)
    ):
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
        superseded = {
            value.lower()
            for value in superseded_publication_digests
        }
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
    if set(authority) != {"id", "status"}:
        raise PublicationValidationError(
            "INVALID_PUBLICATION_AUTHORITY",
            "publication.authority must contain only id and status",
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

    projection_semantics = document.get("projectionSemantics")
    if projection_semantics != PROJECTION_SEMANTICS:
        raise PublicationValidationError(
            "INVALID_PROJECTION_SEMANTICS",
            "openingCivilDate is external Gregorian translation only and may not carry Common Calendar grid authority",
        )

    rows = document.get("years")
    if not isinstance(rows, list):
        raise PublicationValidationError(
            "INVALID_PUBLICATION_ROWS",
            "publication.years must be an array",
        )
    publication_range = validate_publication_rows(rows)

    if (
        expected_first_opening is not None
        and publication_range.first_opening != expected_first_opening
    ):
        raise PublicationValidationError(
            "PUBLICATION_EPOCH_MISMATCH",
            "publication first opening does not match required epoch",
        )

    if (
        expected_first_year is not None
        and publication_range.first_year != expected_first_year
    ):
        raise PublicationValidationError(
            "PUBLICATION_YEAR_EPOCH_MISMATCH",
            "publication first year label does not match required epoch",
        )

    if at_opening is not None:
        if at_opening < publication_range.first_opening:
            raise PublicationValidationError(
                "PUBLICATION_NOT_YET_EFFECTIVE",
                "requested opening predates this publication",
            )
        if at_opening >= publication_range.expires_at_opening:
            raise PublicationValidationError(
                "PUBLICATION_EXPIRED",
                "publication remains historical evidence but its finite projection has ended",
            )

    return PublicationEnvelope(
        publication_version=publication_version,
        calendar_core_spec_version=spec_version,
        authority_id=authority_id,
        authority_status=authority_status,
        publication_range=publication_range,
        publication_digest=normalized_digest,
    )
