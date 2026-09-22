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

from stillpoint.calendar_core.models import GeoPoint
from stillpoint.calendar_core.publication import validate_publication_rows
from stillpoint.calendar_core.reference_rule import SPRING_GATE_ORDINAL, select_v33_nearest_spring_gate, spring_gate_date as core_spring_gate_date
from stillpoint.calendar_core.sunset import apparent_sunset_utc

UTC = dt.timezone.utc


def sunset_utc(civil_date: dt.date, latitude: float, longitude: float) -> dt.datetime:
    return apparent_sunset_utc(civil_date, GeoPoint(latitude, longitude, "PUBLICATION_REFERENCE"))


def parse_utc(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"UTC instant lacks timezone: {value}")
    return parsed.astimezone(UTC)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def coordinate_custody_digest(latitude: float, longitude: float, custody_nonce: str) -> str:
    if len(custody_nonce) < 32:
        raise ValueError("coordinate custody nonce must contain at least 32 characters")
    material = f"GROUND_ZERO\n{latitude:.8f}\n{longitude:.8f}\n{custody_nonce}".encode("utf-8")
    return sha256_bytes(material)


def publication_digest(document: dict[str, Any]) -> str:
    return sha256_bytes(canonical_bytes({key: value for key, value in document.items() if key != "publicationDigest"}))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def equinox_map(document: dict[str, Any]) -> dict[int, dt.datetime]:
    return {int(row["year"]): parse_utc(row["instantUTC"]) for row in document.get("marchEquinoxes", [])}


def spring_gate_date(opening: dt.date) -> dt.date:
    return core_spring_gate_date(opening, SPRING_GATE_ORDINAL)


def choose_reconciliation(*, current_opening: dt.date, next_march_equinox: dt.datetime, latitude: float, longitude: float) -> tuple[int, dt.date]:
    decision = select_v33_nearest_spring_gate(
        current_opening=current_opening,
        next_march_equinox=next_march_equinox,
        reference_point=GeoPoint(latitude, longitude, "PUBLICATION_REFERENCE"),
        spring_gate_ordinal=SPRING_GATE_ORDINAL,
    )
    chosen_gate = decision.immediate_target_date if decision.reconciliation_days == 0 else decision.delayed_target_date
    return decision.reconciliation_days, chosen_gate


def generate(*, latitude: float, longitude: float, first_year_label: int, first_opening: dt.date, count: int, ephemerides: dict[int, dt.datetime], ephemeris_source: str, ephemeris_sha256: str, coordinate_custody_nonce: str, publish_coordinates: bool) -> dict[str, Any]:
    if count < 1:
        raise ValueError("count must be >= 1")

    years: list[dict[str, Any]] = []
    opening = first_opening
    for offset in range(count):
        label = first_year_label + offset
        next_equinox_year = label + 1
        if next_equinox_year not in ephemerides:
            raise ValueError(f"Missing March equinox evidence for {next_equinox_year}")
        equinox = ephemerides[next_equinox_year]
        reconciliation, chosen_gate = choose_reconciliation(
            current_opening=opening,
            next_march_equinox=equinox,
            latitude=latitude,
            longitude=longitude,
        )
        years.append({
            "year": label,
            "openingCivilDate": opening.isoformat(),
            "reconciliationDaysAfterCompletion": reconciliation,
            "governingMarchEquinoxUTC": equinox.isoformat().replace("+00:00", "Z"),
            "nextYearSpringGateCivilDate": chosen_gate.isoformat(),
        })
        opening = opening + dt.timedelta(days=364 + reconciliation)

    reference: dict[str, Any] = {
        "id": "GROUND_ZERO",
        "coordinateCustodyDigest": coordinate_custody_digest(latitude, longitude, coordinate_custody_nonce),
    }
    if publish_coordinates:
        reference["latitude"] = latitude
        reference["longitude"] = longitude

    document: dict[str, Any] = {
        "version": "stillpoint-temporal-v3.3",
        "referencePoint": reference,
        "duskProtocol": {"id": "apparent-sunset-0.8333", "sunCenterAltitudeDegrees": -0.8333},
        "seasonalAnchor": {"event": "march_equinox", "commonMonth": 3, "commonDay": 20, "ordinal": SPRING_GATE_ORDINAL},
        "snapOperator": "NearestLegalSpringGate",
        "ephemerisEvidence": {"source": ephemeris_source, "sha256": ephemeris_sha256},
        "years": years,
    }
    document["publicationDigest"] = publication_digest(document)
    return document


def validate_output(document: dict[str, Any]) -> None:
    supplied_digest = document.get("publicationDigest")
    if not isinstance(supplied_digest, str) or supplied_digest != publication_digest(document):
        raise ValueError("publication digest mismatch")
    if document.get("seasonalAnchor", {}).get("ordinal") != SPRING_GATE_ORDINAL:
        raise ValueError("unexpected seasonal anchor")
    validate_publication_rows(document.get("years", []))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--equinoxes", required=True, type=Path)
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--publish-coordinates", action="store_true")
    args = parser.parse_args()

    ref = load_json(args.reference)
    eph_doc = load_json(args.equinoxes)
    point = ref["referencePoint"]
    latitude = point.get("latitude")
    longitude = point.get("longitude")
    if latitude is None or longitude is None:
        raise SystemExit("Ground Zero latitude/longitude are required in private generation config.")
    custody_nonce = point.get("custodyNonce")
    if custody_nonce is None:
        raise SystemExit("referencePoint.custodyNonce is required")
    first = ref["firstOpening"]
    eph_bytes = args.equinoxes.read_bytes()
    output = generate(
        latitude=float(latitude),
        longitude=float(longitude),
        first_year_label=int(first["yearLabel"]),
        first_opening=dt.date.fromisoformat(first["civilDate"]),
        count=args.count,
        ephemerides=equinox_map(eph_doc),
        ephemeris_source=str(eph_doc["source"]),
        ephemeris_sha256=sha256_bytes(eph_bytes),
        coordinate_custody_nonce=str(custody_nonce),
        publish_coordinates=args.publish_coordinates,
    )
    validate_output(output)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
