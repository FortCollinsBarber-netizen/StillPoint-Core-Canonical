#!/usr/bin/env python3
"""Generate a finite StillPoint Temporal v3.3 Common Calendar publication.

Calendar Core owns astronomy geometry and reference-rule mathematics. This
compiler consumes explicit enactment/evidence inputs and does not duplicate
sunset or Reconciliation law.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

from stillpoint.calendar_core.astronomy import (
    AstronomyEvidence,
    AstronomyEvidenceError,
    MappingAstronomyProvider,
)
from stillpoint.calendar_core.models import GeoPoint, ReconciliationDecision
from stillpoint.calendar_core.publication import (
    PUBLICATION_VERSION,
    publication_digest as core_publication_digest,
    validate_publication_document,
)
from stillpoint.calendar_core.reference_rule import (
    BASE_YEAR_DAYS,
    SPRING_GATE_ORDINAL,
    select_v33_nearest_spring_gate_from_provider,
    spring_gate_date as core_spring_gate_date,
)
from stillpoint.calendar_core.spec import SPEC_VERSION
from stillpoint.calendar_core.sunset import apparent_sunset_utc

UTC = dt.timezone.utc


def sunset_utc(
    civil_date: dt.date,
    latitude: float,
    longitude: float,
) -> dt.datetime:
    return apparent_sunset_utc(
        civil_date,
        GeoPoint(
            latitude,
            longitude,
            "PUBLICATION_REFERENCE",
        ),
    )


def parse_utc(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )
    if parsed.tzinfo is None:
        raise ValueError(
            f"UTC instant lacks timezone: {value}"
        )
    return parsed.astimezone(UTC)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def coordinate_custody_digest(
    latitude: float,
    longitude: float,
    custody_nonce: str,
) -> str:
    if len(custody_nonce) < 32:
        raise ValueError(
            "coordinate custody nonce must contain at least 32 characters"
        )
    material = (
        f"GROUND_ZERO\n{latitude:.8f}\n"
        f"{longitude:.8f}\n{custody_nonce}"
    ).encode("utf-8")
    return sha256_bytes(material)


def publication_digest(
    document: dict[str, Any],
) -> str:
    return core_publication_digest(document)


def load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def equinox_map(
    document: dict[str, Any],
) -> dict[int, dt.datetime]:
    return {
        int(row["year"]): parse_utc(
            row["instantUTC"]
        )
        for row in document.get(
            "marchEquinoxes",
            [],
        )
    }


def spring_gate_date(
    opening: dt.date,
) -> dt.date:
    return core_spring_gate_date(
        opening,
        SPRING_GATE_ORDINAL,
    )


def governing_equinox_year(
    current_opening: dt.date,
) -> int:
    immediate_opening = (
        current_opening
        + dt.timedelta(days=BASE_YEAR_DAYS)
    )
    delayed_opening = (
        immediate_opening
        + dt.timedelta(days=7)
    )
    immediate_gate = spring_gate_date(
        immediate_opening
    )
    delayed_gate = spring_gate_date(
        delayed_opening
    )

    if immediate_gate.year != delayed_gate.year:
        raise ValueError(
            "candidate Spring Gates cross civil years; "
            "governing equinox year must be explicitly resolved"
        )

    return immediate_gate.year


def astronomy_provider(
    *,
    ephemerides: dict[int, dt.datetime],
    ephemeris_source: str,
    ephemeris_sha256: str,
) -> MappingAstronomyProvider:
    evidence = {
        year: AstronomyEvidence(
            event="march_equinox",
            year=year,
            instant_utc=instant,
            source_id=ephemeris_source,
            evidence_sha256=ephemeris_sha256,
        )
        for year, instant in ephemerides.items()
    }
    return MappingAstronomyProvider(
        provider_id=ephemeris_source,
        evidence_by_year=evidence,
    )


def choose_reconciliation(
    *,
    current_opening: dt.date,
    evidence_year: int,
    provider: MappingAstronomyProvider,
    latitude: float,
    longitude: float,
) -> ReconciliationDecision:
    return select_v33_nearest_spring_gate_from_provider(
        current_opening=current_opening,
        evidence_year=evidence_year,
        provider=provider,
        reference_point=GeoPoint(
            latitude,
            longitude,
            "PUBLICATION_REFERENCE",
        ),
        spring_gate_ordinal=SPRING_GATE_ORDINAL,
    )


def generate(
    *,
    latitude: float,
    longitude: float,
    first_year_label: int,
    first_opening: dt.date,
    count: int,
    ephemerides: dict[int, dt.datetime],
    ephemeris_source: str,
    ephemeris_sha256: str,
    coordinate_custody_nonce: str,
    publish_coordinates: bool,
    authority_id: str = "UNRATIFIED_PILOT",
    authority_status: str = "pilot",
    reference_point_id: str = "GROUND_ZERO",
) -> dict[str, Any]:
    if count < 1:
        raise ValueError("count must be >= 1")

    provider = astronomy_provider(
        ephemerides=ephemerides,
        ephemeris_source=ephemeris_source,
        ephemeris_sha256=ephemeris_sha256,
    )

    years: list[dict[str, Any]] = []
    opening = first_opening

    for offset in range(count):
        label = first_year_label + offset
        evidence_year = governing_equinox_year(
            opening
        )
        decision = choose_reconciliation(
            current_opening=opening,
            evidence_year=evidence_year,
            provider=provider,
            latitude=latitude,
            longitude=longitude,
        )

        years.append(
            {
                "year": label,
                "openingCivilDate": opening.isoformat(),
                "reconciliationDaysAfterCompletion":
                    decision.reconciliation_days,
                "reconciliationReasonCode":
                    decision.reason_code,
                "governingMarchEquinoxYear":
                    evidence_year,
                "governingMarchEquinoxUTC":
                    decision.evidence_instant_utc
                    .astimezone(UTC)
                    .isoformat()
                    .replace("+00:00", "Z"),
                "immediateCandidateOpeningCivilDate":
                    decision.immediate_candidate_opening
                    .isoformat(),
                "delayedCandidateOpeningCivilDate":
                    decision.delayed_candidate_opening
                    .isoformat(),
                "immediateSpringGateCivilDate":
                    decision.immediate_target_date
                    .isoformat(),
                "delayedSpringGateCivilDate":
                    decision.delayed_target_date
                    .isoformat(),
                "immediateErrorSeconds":
                    decision.immediate_error_seconds,
                "delayedErrorSeconds":
                    decision.delayed_error_seconds,
                "nextYearSpringGateCivilDate":
                    decision.selected_target_date
                    .isoformat(),
            }
        )

        opening = decision.selected_candidate_opening

    reference: dict[str, Any] = {
        "id": reference_point_id,
        "coordinateCustodyDigest":
            coordinate_custody_digest(
                latitude,
                longitude,
                coordinate_custody_nonce,
            ),
    }

    if publish_coordinates:
        reference["latitude"] = latitude
        reference["longitude"] = longitude

    document: dict[str, Any] = {
        "publicationVersion":
            PUBLICATION_VERSION,
        "calendarCoreSpecVersion":
            SPEC_VERSION,
        "version":
            "stillpoint-temporal-v3.3",
        "authority": {
            "id": authority_id,
            "status": authority_status,
        },
        "referenceRuleVersion":
            "v3.3-candidate",
        "referencePoint": reference,
        "duskProtocol": {
            "id":
                "apparent-sunset-0.8333",
            "sunCenterAltitudeDegrees":
                -0.8333,
        },
        "seasonalAnchor": {
            "event": "march_equinox",
            "commonMonth": 3,
            "commonDay": 20,
            "ordinal":
                SPRING_GATE_ORDINAL,
        },
        "snapOperator":
            "NearestLegalSpringGate",
        "ephemerisEvidence": {
            "source":
                ephemeris_source,
            "sha256":
                ephemeris_sha256,
        },
        "years": years,
    }

    document["publicationDigest"] = (
        publication_digest(document)
    )
    return document


def validate_output(
    document: dict[str, Any],
) -> None:
    supplied_digest = document.get(
        "publicationDigest"
    )
    if (
        not isinstance(supplied_digest, str)
        or supplied_digest
        != publication_digest(document)
    ):
        raise ValueError(
            "publication digest mismatch"
        )

    if (
        document.get(
            "seasonalAnchor",
            {},
        ).get("ordinal")
        != SPRING_GATE_ORDINAL
    ):
        raise ValueError(
            "unexpected seasonal anchor"
        )

    validate_publication_document(
        document
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reference",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--equinoxes",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--count",
        type=int,
        default=100,
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--publish-coordinates",
        action="store_true",
    )
    args = parser.parse_args()

    ref = load_json(args.reference)
    eph_doc = load_json(args.equinoxes)

    point = ref["referencePoint"]
    latitude = point.get("latitude")
    longitude = point.get("longitude")

    if latitude is None or longitude is None:
        raise SystemExit(
            "referencePoint latitude/longitude "
            "are required in private generation config."
        )

    custody_nonce = point.get(
        "custodyNonce"
    )
    if custody_nonce is None:
        raise SystemExit(
            "referencePoint.custodyNonce is required"
        )

    authority = ref.get(
        "publicationAuthority"
    )
    if not isinstance(authority, dict):
        raise SystemExit(
            "publicationAuthority is required"
        )

    authority_id = authority.get("id")
    authority_status = authority.get(
        "status"
    )

    if (
        not isinstance(authority_id, str)
        or not authority_id.strip()
    ):
        raise SystemExit(
            "publicationAuthority.id is required"
        )

    if authority_status not in (
        "pilot",
        "enacted",
    ):
        raise SystemExit(
            "publicationAuthority.status must "
            "be either pilot or enacted"
        )

    first = ref["firstOpening"]
    eph_bytes = args.equinoxes.read_bytes()

    output = generate(
        latitude=float(latitude),
        longitude=float(longitude),
        first_year_label=int(
            first["yearLabel"]
        ),
        first_opening=dt.date.fromisoformat(
            first["civilDate"]
        ),
        count=args.count,
        ephemerides=equinox_map(eph_doc),
        ephemeris_source=str(
            eph_doc["source"]
        ),
        ephemeris_sha256=sha256_bytes(
            eph_bytes
        ),
        coordinate_custody_nonce=str(
            custody_nonce
        ),
        publish_coordinates=
            args.publish_coordinates,
        authority_id=
            authority_id.strip(),
        authority_status=
            authority_status,
        reference_point_id=str(
            point.get("id")
            or "UNSPECIFIED_REFERENCE"
        ),
    )

    validate_output(output)

    args.output.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
