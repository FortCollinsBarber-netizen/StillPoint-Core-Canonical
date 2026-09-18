#!/usr/bin/env python3
"""Generate a StillPoint Temporal v3.3 Common Calendar publication.

v3.3 keeps three questions separate:
- annual form: always 364 ordinary dusk-days;
- weekday sequence: continuous, with only whole-week interannual correction;
- seasonal truth: the fixed Common March 20 Spring Gate is compared with the
  next astronomical March equinox.

The year opening is therefore not forced to be the equinox itself. This lets
fixed civic month/day labels and solar honesty coexist.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
from typing import Any

UTC = dt.timezone.utc
SUNSET_ZENITH_DEG = 90.8333
SPRING_GATE_ORDINAL = 80  # Common Month 3 Day 20 in 30/30/31 x 4.


def _norm_deg(value: float) -> float:
    return value % 360.0


def _norm_hours(value: float) -> float:
    return value % 24.0


def _deg2rad(value: float) -> float:
    return math.radians(value)


def _rad2deg(value: float) -> float:
    return math.degrees(value)


def sunset_utc(civil_date: dt.date, latitude: float, longitude: float) -> dt.datetime:
    ordinal = civil_date.timetuple().tm_yday
    lng_hour = longitude / 15.0
    t = ordinal + ((18.0 - lng_hour) / 24.0)

    mean_anomaly = (0.9856 * t) - 3.289
    true_longitude = _norm_deg(
        mean_anomaly
        + 1.916 * math.sin(_deg2rad(mean_anomaly))
        + 0.020 * math.sin(_deg2rad(2.0 * mean_anomaly))
        + 282.634
    )

    right_ascension = _norm_deg(
        _rad2deg(math.atan(0.91764 * math.tan(_deg2rad(true_longitude))))
    )
    l_quadrant = math.floor(true_longitude / 90.0) * 90.0
    ra_quadrant = math.floor(right_ascension / 90.0) * 90.0
    right_ascension = (right_ascension + l_quadrant - ra_quadrant) / 15.0

    sin_declination = 0.39782 * math.sin(_deg2rad(true_longitude))
    cos_declination = math.cos(math.asin(sin_declination))

    cos_hour = (
        math.cos(_deg2rad(SUNSET_ZENITH_DEG))
        - sin_declination * math.sin(_deg2rad(latitude))
    ) / (cos_declination * math.cos(_deg2rad(latitude)))

    if not -1.0 <= cos_hour <= 1.0:
        raise ValueError(f"No standardized sunset on {civil_date.isoformat()}")

    hour_angle = _rad2deg(math.acos(cos_hour)) / 15.0
    local_mean_time = hour_angle + right_ascension - (0.06571 * t) - 6.622
    local_mean_hours = _norm_hours(local_mean_time)
    utc_hours = local_mean_hours - lng_hour

    midnight = dt.datetime.combine(civil_date, dt.time(0, 0), tzinfo=UTC)
    return midnight + dt.timedelta(hours=utc_hours)


def parse_utc(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"UTC instant lacks timezone: {value}")
    return parsed.astimezone(UTC)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def coordinate_custody_digest(
    latitude: float,
    longitude: float,
    custody_nonce: str,
) -> str:
    if len(custody_nonce) < 32:
        raise ValueError("coordinate custody nonce must contain at least 32 characters")
    material = (
        f"GROUND_ZERO\n{latitude:.8f}\n{longitude:.8f}\n{custody_nonce}"
    ).encode("utf-8")
    return sha256_bytes(material)


def publication_digest(document: dict[str, Any]) -> str:
    unsigned = {
        key: value for key, value in document.items()
        if key != "publicationDigest"
    }
    return sha256_bytes(canonical_bytes(unsigned))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def equinox_map(document: dict[str, Any]) -> dict[int, dt.datetime]:
    result: dict[int, dt.datetime] = {}
    for row in document.get("marchEquinoxes", []):
        result[int(row["year"])] = parse_utc(row["instantUTC"])
    return result


def spring_gate_date(opening: dt.date) -> dt.date:
    return opening + dt.timedelta(days=SPRING_GATE_ORDINAL - 1)


def choose_reconciliation(
    *,
    current_opening: dt.date,
    next_march_equinox: dt.datetime,
    latitude: float,
    longitude: float,
) -> tuple[int, dt.date]:
    immediate_opening = current_opening + dt.timedelta(days=364)
    delayed_opening = immediate_opening + dt.timedelta(days=7)

    immediate_gate = spring_gate_date(immediate_opening)
    delayed_gate = spring_gate_date(delayed_opening)

    immediate_error = abs(
        (sunset_utc(immediate_gate, latitude, longitude) - next_march_equinox)
        .total_seconds()
    )
    delayed_error = abs(
        (sunset_utc(delayed_gate, latitude, longitude) - next_march_equinox)
        .total_seconds()
    )

    if immediate_error <= delayed_error:
        return 0, immediate_gate
    return 7, delayed_gate


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
) -> dict[str, Any]:
    if count < 1:
        raise ValueError("count must be >= 1")

    years: list[dict[str, Any]] = []
    opening = first_opening

    for offset in range(count):
        label = first_year_label + offset
        next_equinox_year = label + 1
        if next_equinox_year not in ephemerides:
            raise ValueError(
                f"Missing March equinox evidence for {next_equinox_year}"
            )

        equinox = ephemerides[next_equinox_year]
        reconciliation, chosen_gate = choose_reconciliation(
            current_opening=opening,
            next_march_equinox=equinox,
            latitude=latitude,
            longitude=longitude,
        )

        years.append(
            {
                "year": label,
                "openingCivilDate": opening.isoformat(),
                "reconciliationDaysAfterCompletion": reconciliation,
                "governingMarchEquinoxUTC": (
                    equinox.isoformat().replace("+00:00", "Z")
                ),
                "nextYearSpringGateCivilDate": chosen_gate.isoformat(),
            }
        )

        opening = opening + dt.timedelta(days=364 + reconciliation)

    reference: dict[str, Any] = {
        "id": "GROUND_ZERO",
        "coordinateCustodyDigest": coordinate_custody_digest(
            latitude, longitude, coordinate_custody_nonce
        ),
    }
    if publish_coordinates:
        reference["latitude"] = latitude
        reference["longitude"] = longitude

    document: dict[str, Any] = {
        "version": "stillpoint-temporal-v3.3",
        "referencePoint": reference,
        "duskProtocol": {
            "id": "apparent-sunset-0.8333",
            "sunCenterAltitudeDegrees": -0.8333,
        },
        "seasonalAnchor": {
            "event": "march_equinox",
            "commonMonth": 3,
            "commonDay": 20,
            "ordinal": SPRING_GATE_ORDINAL,
        },
        "snapOperator": "NearestLegalSpringGate",
        "ephemerisEvidence": {
            "source": ephemeris_source,
            "sha256": ephemeris_sha256,
        },
        "years": years,
    }
    document["publicationDigest"] = publication_digest(document)
    return document


def validate_output(document: dict[str, Any]) -> None:
    supplied_digest = document.get("publicationDigest")
    if (
        not isinstance(supplied_digest, str)
        or supplied_digest != publication_digest(document)
    ):
        raise ValueError("publication digest mismatch")

    anchor = document.get("seasonalAnchor", {})
    if anchor.get("ordinal") != SPRING_GATE_ORDINAL:
        raise ValueError("unexpected seasonal anchor")

    rows = document["years"]
    if not rows:
        raise ValueError("publication has no year rows")

    for index, row in enumerate(rows):
        reconciliation = row["reconciliationDaysAfterCompletion"]
        if reconciliation not in (0, 7):
            raise ValueError("illegal reconciliation value")

        if index + 1 < len(rows):
            current = dt.date.fromisoformat(row["openingCivilDate"])
            nxt = dt.date.fromisoformat(rows[index + 1]["openingCivilDate"])
            expected = 364 + reconciliation
            actual = (nxt - current).days
            if actual != expected:
                raise ValueError(
                    f"opening span mismatch at year {row['year']}: "
                    f"expected {expected}, got {actual}"
                )


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
        raise SystemExit(
            "Ground Zero latitude/longitude are required in private generation config."
        )

    custody_nonce = point.get("custodyNonce")
    if custody_nonce is None:
        raise SystemExit("referencePoint.custodyNonce is required")

    first = ref["firstOpening"]
    first_year_label = int(first["yearLabel"])
    first_opening = dt.date.fromisoformat(first["civilDate"])

    eph_bytes = args.equinoxes.read_bytes()
    output = generate(
        latitude=float(latitude),
        longitude=float(longitude),
        first_year_label=first_year_label,
        first_opening=first_opening,
        count=args.count,
        ephemerides=equinox_map(eph_doc),
        ephemeris_source=str(eph_doc["source"]),
        ephemeris_sha256=sha256_bytes(eph_bytes),
        coordinate_custody_nonce=str(custody_nonce),
        publish_coordinates=args.publish_coordinates,
    )
    validate_output(output)
    args.output.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
