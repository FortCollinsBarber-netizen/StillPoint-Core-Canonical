#!/usr/bin/env python3
"""Generate a finite fixed-364 Common Calendar publication.

The filename is retained as a compatibility entry point for the former v3.3
toolchain. Reconciliation and equinox snapping are no longer operative law.
Astronomical evidence may be carried as witness provenance only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

from stillpoint.calendar_core.publication import (
    PUBLICATION_VERSION,
    publication_digest as core_publication_digest,
    validate_publication_document,
)
from stillpoint.calendar_core.spec import SPEC_VERSION


def parse_utc(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )
    if parsed.tzinfo is None:
        raise ValueError(
            f"UTC instant lacks timezone: {value}"
        )
    return parsed.astimezone(dt.timezone.utc)


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
    del ephemerides
    if count < 1:
        raise ValueError("count must be >= 1")

    years = [
        {
            "year": first_year_label + offset,
            "openingCivilDate": (
                first_opening
                + dt.timedelta(days=364 * offset)
            ).isoformat(),
            "reconciliationDaysAfterCompletion": 0,
        }
        for offset in range(count)
    ]

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
        "publicationVersion": PUBLICATION_VERSION,
        "calendarCoreSpecVersion": SPEC_VERSION,
        "version": "stillpoint-fixed-364-v1",
        "authority": {
            "id": authority_id,
            "status": authority_status,
        },
        "referenceRuleVersion": "fixed-364-v1",
        "referencePoint": reference,
        "gridRule": {
            "yearDays": 364,
            "weekDays": 7,
            "yearCount": count,
            "reconciliationDays": 0,
        },
        "ephemerisEvidence": {
            "source": ephemeris_source,
            "sha256": ephemeris_sha256,
            "role": "witness-only-no-grid-authority",
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

    if document.get(
        "referenceRuleVersion"
    ) != "fixed-364-v1":
        raise ValueError(
            "publication must use fixed-364-v1"
        )

    for row in document.get("years", []):
        if row.get(
            "reconciliationDaysAfterCompletion"
        ) != 0:
            raise ValueError(
                "reconciliation is prohibited"
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
        help=(
            "astronomical witness file; retained for provenance "
            "but cannot alter the fixed grid"
        ),
    )
    parser.add_argument(
        "--count",
        type=int,
        default=50,
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
        ephemerides={},
        ephemeris_source=str(
            eph_doc.get("source")
            or "UNSPECIFIED_WITNESS"
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
