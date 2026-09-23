"""Read-only runtime projection for the enacted finite Common Calendar.

This module exposes Calendar Core data without constructing CompanyRuntime or
opening company state. Calendar law remains owned by stillpoint.calendar_core;
this is only a bounded projection surface for clients such as RobertOS.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .calendar import CANONICAL_DAY001_WEEKDAY
from .population import address_from_ordinal
from .publication import validate_publication_document
from .models import GeoPoint
from .sunset import bracket_sunset
from .week import protected_time_state
from .lunar import lunar_phase_state

PUBLICATION_FILENAME = "calendar_publication_2026_2075.json"
RUNTIME_SCHEMA = "stillpoint.calendar-day.v1"


def default_publication_path() -> Path:
    return Path(__file__).resolve().parent.parent / "contracts" / PUBLICATION_FILENAME


def load_enacted_publication(path: Path | str | None = None) -> dict[str, Any]:
    publication_path = Path(path) if path is not None else default_publication_path()
    document = json.loads(publication_path.read_text(encoding="utf-8"))
    validate_publication_document(document, require_authority_status="enacted")
    rows = document.get("years")
    if not isinstance(rows, list) or len(rows) != 50:
        raise ValueError("runtime calendar requires the enacted 50-year publication")
    return document


def calendar_day_payload(
    year: int,
    ordinal: int,
    *,
    publication_path: Path | str | None = None,
) -> dict[str, Any]:
    document = load_enacted_publication(publication_path)
    rows = document["years"]
    first_year = int(rows[0]["year"])
    last_year = int(rows[-1]["year"])

    day = address_from_ordinal(
        publication_document=document,
        year=int(year),
        ordinal=int(ordinal),
        jubilee_epoch_common_year=first_year,
        jubilee_epoch_cycle=1,
    )

    authority = document.get("authority") or {}
    return {
        "schema": RUNTIME_SCHEMA,
        "authority": "read-only-calendar-law",
        "calendar_address": day.calendar_address,
        "common_date": {
            "year": day.year,
            "month": day.month,
            "day": day.day,
            "ordinal": day.ordinal,
            "week": day.week,
            "day_in_week": day.day_in_week,
            "weekday": day.weekday,
        },
        "civil_window": {
            "opens": day.opening_civil_date.isoformat(),
            "closes": day.closes_on_civil_date.isoformat(),
        },
        "season": {
            "number": day.quarter,
            "day": day.day_of_quarter,
            "enoch_phase": day.enoch_phase,
            "enoch_gate": day.enoch_gate,
            "enoch_motion": day.enoch_motion,
        },
        "protected_time": {
            "is_sabbath": day.is_sabbath_date,
        },
        "observances": [
            {"id": oid, "name": name}
            for oid, name in zip(day.observance_ids, day.observance_names)
        ],
        "jubilee": {
            "cycle": day.jubilee_cycle,
            "year": day.jubilee_year,
            "is_sabbatical_threshold": day.is_sabbatical_threshold,
            "is_jubilee_year": day.is_jubilee_year,
            "is_jubilee_release_day": day.is_jubilee_release_day,
        },
        "provenance": list(day.source_refs),
        "publication": {
            "version": document.get("publicationVersion"),
            "digest": document.get("publicationDigest"),
            "authority_id": authority.get("id"),
            "authority_status": authority.get("status"),
        },
        "map": {
            "first_year": first_year,
            "last_year": last_year,
            "year_count": len(rows),
            "total_days": len(rows) * 364,
            "day001_weekday": CANONICAL_DAY001_WEEKDAY,
            "year_days": 364,
            "weeks_per_year": 52,
            "december_31_exists": False,
        },
    }


CLOCK_RUNTIME_SCHEMA = "stillpoint.clock-snapshot.v1"


def _current_publication_day(
    instant: datetime,
    *,
    latitude: float,
    longitude: float,
    local_zone: str,
    publication_path: Path | str | None = None,
) -> tuple[dict[str, Any], Any, Any]:
    if instant.tzinfo is None:
        raise ValueError("instant must be timezone-aware")

    document = load_enacted_publication(publication_path)
    location = GeoPoint(
        latitude=float(latitude),
        longitude=float(longitude),
        id="runtime-location",
    )
    pair = bracket_sunset(instant, location, local_zone)
    boundary_date = pair.previous_civil_date

    rows = document["years"]
    for index, row in enumerate(rows):
        opening = date.fromisoformat(str(row["openingCivilDate"]))
        if index + 1 < len(rows):
            expires = date.fromisoformat(
                str(rows[index + 1]["openingCivilDate"])
            )
        else:
            expires = opening + timedelta(days=364)

        if opening <= boundary_date < expires:
            ordinal = (boundary_date - opening).days + 1
            return (
                calendar_day_payload(
                    int(row["year"]),
                    ordinal,
                    publication_path=publication_path,
                ),
                location,
                pair,
            )

    raise ValueError("instant is outside enacted 50-year calendar publication")


def clock_snapshot_payload(
    instant: datetime,
    *,
    latitude: float,
    longitude: float,
    local_zone: str,
    publication_path: Path | str | None = None,
) -> dict[str, Any]:
    day, location, pair = _current_publication_day(
        instant,
        latitude=latitude,
        longitude=longitude,
        local_zone=local_zone,
        publication_path=publication_path,
    )
    weekly = protected_time_state(
        instant,
        location=location,
        local_zone=local_zone,
    )
    lunar = lunar_phase_state(instant)

    return {
        "schema": CLOCK_RUNTIME_SCHEMA,
        "authority": "read-only-clock-projection",
        "instant_utc": instant.astimezone(timezone.utc).isoformat(),
        "location": {
            "latitude": float(latitude),
            "longitude": float(longitude),
            "coordinate_system": "WGS84",
            "local_zone": local_zone,
        },
        "calendar": day,
        "solar_boundaries": {
            "previous_sunset_utc": pair.previous.astimezone(
                timezone.utc
            ).isoformat(),
            "next_sunset_utc": pair.next.astimezone(
                timezone.utc
            ).isoformat(),
            "previous_boundary_civil_date":
                pair.previous_civil_date.isoformat(),
            "next_boundary_civil_date":
                pair.next_civil_date.isoformat(),
        },
        "protected_time": {
            "named_day": weekly.named_day,
            "sabbath_active": weekly.is_sabbath,
            "lords_day_active": weekly.is_lords_day,
            "stillpoint_active": weekly.is_stillpoint,
            "next_boundary_utc": (
                weekly.next_protected_boundary.astimezone(
                    timezone.utc
                ).isoformat()
                if weekly.next_protected_boundary
                else None
            ),
            "next_boundary_label":
                weekly.next_protected_boundary_label,
        },
        "lunar": {
            "phase": lunar.phase_name,
            "waxing": lunar.is_waxing,
            "age_days": round(lunar.age_days, 6),
            "illumination_fraction": round(
                lunar.illumination_fraction,
                8,
            ),
            "illumination_percent": lunar.illumination_percent,
            "jurisdiction": "witness-only-no-grid-mutation",
            "evidence": lunar.evidence_label,
        },
    }
