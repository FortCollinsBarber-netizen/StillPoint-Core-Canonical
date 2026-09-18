#!/usr/bin/env python3
"""Generate a StillPoint Temporal v3.3 Common Calendar publication.

The generator is deliberately evidence-fed:
- it does not invent Ground Zero coordinates;
- it does not invent March equinox instants;
- it never emits a correction other than 0 or 7 days;
- it treats the ordinary year as complete after 364 local sunset boundaries.

Input coordinates and ephemeris evidence are supplied explicitly.
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


def _norm_deg(value: float) -> float:
    return value % 360.0


def _norm_hours(value: float) -> float:
    return value % 24.0


def _deg2rad(value: float) -> float:
    return math.radians(value)


def _rad2deg(value: float) -> float:
    return math.degrees(value)


def sunset_utc(civil_date: dt.date, latitude: float, longitude: float) -> dt.datetime:
    """NOAA-style standardized apparent-sunset approximation.

    This computes the legal comparison boundary from an idealized apparent
    sunset geometry. It is deterministic and suitable for generation/testing.
    An enacted production release should still identify the authoritative
    ephemeris/source used for the annual March-equinox evidence.
    """

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

    # Do not normalize the UTC hour before attaching it to the date.
    # For western longitudes an evening sunset can legitimately be >24 UTC
    # hours from UTC midnight bearing the same civil-date label (for example,
    # Colorado sunset is often early UTC on the following day). Preserving the
    # raw offset lets timedelta carry the instant across the UTC date boundary.
    # Normalizing here would silently move the comparison boundary by 24 hours.
    utc_hours = local_mean_time - lng_hour

    midnight = dt.datetime.combine(civil_date, dt.time(0, 0), tzinfo=UTC)
    return midnight + dt.timedelta(hours=utc_hours)


def parse_utc(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"UTC instant lacks timezone: {value}")
    return parsed.astimezone(UTC)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def coordinate_digest(latitude: float, longitude: float) -> str:
    material = f"{latitude:.8f},{longitude:.8f}".encode("ascii")
    return sha256_bytes(material)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def equinox_map(document: dict[str, Any]) -> dict[int, dt.datetime]:
    rows = document.get("marchEquinoxes", [])
    result: dict[int, dt.datetime] = {}
    for row in rows:
        year = int(row["year"])
        result[year] = parse_utc(row["instantUTC"])
    return result


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
    publish_coordinates: bool,
) -> dict[str, Any]:
    if count < 1:
        raise ValueError("count must be >= 1")

    years: list[dict[str, Any]] = []
    opening = first_opening

    for offset in range(count):
        label = first_year_label + offset

        if offset == count - 1:
            # The final row still needs a declared reconciliation value. We
            # require next-year ephemeris evidence so no terminal row guesses.
            next_equinox_year = label + 1
        else:
            next_equinox_year = label + 1

        if next_equinox_year not in ephemerides:
            raise ValueError(
                f"Missing March equinox evidence for {next_equinox_year}"
            )

        equinox = ephemerides[next_equinox_year]
        immediate_date = opening + dt.timedelta(days=364)
        delayed_date = immediate_date + dt.timedelta(days=7)

        immediate_sunset = sunset_utc(immediate_date, latitude, longitude)
        delayed_sunset = sunset_utc(delayed_date, latitude, longitude)

        immediate_error = abs((immediate_sunset - equinox).total_seconds())
        delayed_error = abs((delayed_sunset - equinox).total_seconds())

        reconciliation = 0 if immediate_error <= delayed_error else 7

        years.append(
            {
                "year": label,
                "openingCivilDate": opening.isoformat(),
                "reconciliationDaysAfterCompletion": reconciliation,
                "governingMarchEquinoxUTC": equinox.isoformat().replace("+00:00", "Z"),
            }
        )

        opening = immediate_date + dt.timedelta(days=reconciliation)

    reference: dict[str, Any] = {
        "id": "GROUND_ZERO",
        "coordinateDigest": coordinate_digest(latitude, longitude),
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
        "snapOperator": "NearestLegalReentry",
        "ephemerisEvidence": {
            "source": ephemeris_source,
            "sha256": ephemeris_sha256,
        },
        "years": years,
    }

    digest = sha256_bytes(canonical_bytes(document))
    document["publicationDigest"] = digest
    return document


def validate_output(document: dict[str, Any]) -> None:
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
    parser.add_argument(
        "--publish-coordinates",
        action="store_true",
        help="Include Ground Zero coordinates in published JSON.",
    )
    args = parser.parse_args()

    ref = load_json(args.reference)
    eph_doc = load_json(args.equinoxes)

    point = ref["referencePoint"]
    latitude = point.get("latitude")
    longitude = point.get("longitude")
    if latitude is None or longitude is None:
        raise SystemExit(
            "Ground Zero latitude/longitude are required in the private "
            "generation config; example placeholders are intentionally null."
        )

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
        publish_coordinates=args.publish_coordinates,
    )
    validate_output(output)

    args.output.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
