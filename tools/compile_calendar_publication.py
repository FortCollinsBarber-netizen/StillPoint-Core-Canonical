#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from stillpoint.calendar_core.models import GeoPoint
from stillpoint.calendar_publication import compile_v33_publication


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("ephemeris instant must be timezone-aware")
    return parsed


def _equinox_map(document: dict[str, Any]) -> dict[int, datetime]:
    return {
        int(row["year"]): _parse_utc(row["instantUTC"])
        for row in document.get("marchEquinoxes", [])
    }


def _coordinate_digest(latitude: float, longitude: float, nonce: str) -> str:
    if len(nonce) < 32:
        raise ValueError("custody nonce must contain at least 32 characters")
    raw = f"{latitude:.8f}\n{longitude:.8f}\n{nonce}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--equinoxes", required=True, type=Path)
    parser.add_argument("--count", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    reference = _load_json(args.reference)
    evidence = _load_json(args.equinoxes)
    point = reference["referencePoint"]

    latitude = point.get("latitude")
    longitude = point.get("longitude")
    nonce = point.get("custodyNonce")
    if latitude is None or longitude is None:
        raise SystemExit("reference coordinates are required for compilation")
    if nonce is None:
        raise SystemExit("referencePoint.custodyNonce is required")

    first = reference["firstOpening"]
    evidence_bytes = args.equinoxes.read_bytes()
    document = compile_v33_publication(
        publication_id=str(reference["publicationId"]),
        authority_status=str(reference["authority"]["status"]),
        authority_id=str(reference["authority"]["authorityId"]),
        reference_point=GeoPoint(
            float(latitude),
            float(longitude),
            str(point["id"]),
        ),
        reference_point_id=str(point["id"]),
        reference_geometry_digest=_coordinate_digest(
            float(latitude),
            float(longitude),
            str(nonce),
        ),
        first_year_label=int(first["yearLabel"]),
        first_opening=date.fromisoformat(first["civilDate"]),
        first_opening_continuous_k=int(first["continuousK"]),
        day001_weekday=str(first["day001Weekday"]),
        count=args.count,
        march_equinoxes=_equinox_map(evidence),
        evidence_source_id=str(evidence["source"]),
        evidence_digest=hashlib.sha256(evidence_bytes).hexdigest(),
    )

    args.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
