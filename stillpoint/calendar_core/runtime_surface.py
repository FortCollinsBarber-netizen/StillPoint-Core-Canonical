"""Read-only runtime projection for the enacted finite Common Calendar.

This module exposes Calendar Core data without constructing CompanyRuntime or
opening company state. Calendar law remains owned by stillpoint.calendar_core;
this is only a bounded projection surface for clients such as RobertOS.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .calendar import CANONICAL_DAY001_WEEKDAY
from .governor import (
    CanonicalDate,
    RHYTHM_GOVERNOR,
    RhythmAuthority,
    RhythmRequest,
)
from .population import address_from_ordinal
from .publication import validate_publication_document

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
    RHYTHM_GOVERNOR.require(
        RhythmRequest(
            authority=RhythmAuthority.READ,
            source="calendar-runtime-surface",
            canonical_date=CanonicalDate(day.year, day.month, day.day),
        )
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
        "common_civil_coordinate": {
            "date": f"{day.year:04d}-{day.month:02d}-{day.day:02d}",
            "clock": "24-hour",
            "date_boundary": "00:00",
            "daylight_saving_time": False,
            "role": "coordination-coordinate",
        },
        "civil_window": {
            "opens": day.opening_civil_date.isoformat(),
            "closes": day.closes_on_civil_date.isoformat(),
            "frame": "proleptic-gregorian",
            "role": "external-translation-only",
            "grid_authority": False,
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
