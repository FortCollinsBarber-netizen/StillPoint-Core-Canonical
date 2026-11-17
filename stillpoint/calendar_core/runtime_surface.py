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
from .long_cycles import JubileeConfiguration, compare_long_cycles
from .observances import observances_for_ordinal
from .jubilee import jubilee_state
from .sacred import (
    JUBILEE_EPOCH_COMMON_YEAR, PROFILE_STATUS, sacred_from_common,
    sacred_profile_payload, long_cycle_policy_payload,
)
from .publication import validate_publication_document
from .witness_overlays import witnesses_for_external_date

PUBLICATION_FILENAME = "calendar_publication_2026_2075.json"
RUNTIME_SCHEMA = "stillpoint.calendar-day.v2"


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
    jubilee_configuration: JubileeConfiguration | None = None,
) -> dict[str, Any]:
    """Project a published day with visible, separately scoped cycle inputs.

    Omitting the configuration uses the declared project profile. Passing a configuration never changes the
    annual grid or extends publication coverage. None as its epoch explicitly
    requests no Jubilee designation.
    """
    document = load_enacted_publication(publication_path)
    rows = document["years"]
    first_year = int(rows[0]["year"])
    last_year = int(rows[-1]["year"])
    if jubilee_configuration is not None and not isinstance(
        jubilee_configuration, JubileeConfiguration
    ):
        raise ValueError("jubilee_configuration must be a JubileeConfiguration")
    configuration = (
        jubilee_configuration
        if jubilee_configuration is not None
        else JubileeConfiguration(epoch_common_year=JUBILEE_EPOCH_COMMON_YEAR)
    )

    day = address_from_ordinal(
        publication_document=document,
        year=int(year),
        ordinal=int(ordinal),
        jubilee_epoch_common_year=configuration.epoch_common_year,
        jubilee_epoch_cycle=configuration.epoch_cycle,
        jubilee_rollover_rule=configuration.rollover_rule,
    )
    RHYTHM_GOVERNOR.require(
        RhythmRequest(
            authority=RhythmAuthority.READ,
            source="calendar-runtime-surface",
            canonical_date=CanonicalDate(day.year, day.month, day.day),
        )
    )

    authority = document.get("authority") or {}
    cycle_state = jubilee_state(
        common_year=day.year, epoch_common_year=configuration.epoch_common_year,
        epoch_cycle=configuration.epoch_cycle, rollover_rule=configuration.rollover_rule,
    )
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
        "sacred_date": sacred_from_common(day.year, day.month, day.day),
        "sacred_year_profile": sacred_profile_payload(),
        "long_cycle_policy": long_cycle_policy_payload(),
        "civil_window": {
            "opens": day.opening_civil_date.isoformat(),
            "closes": day.closes_on_civil_date.isoformat(),
            "frame": "proleptic-gregorian",
            "role": "external-translation-only",
            "grid_authority": False,
        },
        "external_witness_overlays": [
            event.as_payload()
            for event in witnesses_for_external_date(day.opening_civil_date)
        ],
        "season": {
            "number": day.quarter,
            "day": day.day_of_quarter,
            "enoch_phase": day.enoch_phase,
            "enoch_gate": day.enoch_gate,
            "enoch_motion": day.enoch_motion,
        },
        "protected_time": {
            "is_sabbath_date": day.is_sabbath_date,
            "sabbath_opens": "Friday local sunset",
            "sabbath_closes": "Saturday local sunset",
            "stillpoint_opens": "Friday civil dusk (solar center -6 degrees)",
            "stillpoint_releases": "Sunday civil dawn (solar center -6 degrees)",
            "boundary_authority": "local-light-overlay-no-grid-mutation",
        },
        "observances": [
            {
                "id": item.id,
                "name": item.name,
                "jurisdiction": item.jurisdiction,
                "rule": item.rule,
                "source_refs": list(item.source_refs),
                "note": item.note,
                "common_coordinate": {"month": item.month, "day": item.day},
                "source_coordinate": (
                    {"calendar": item.source_calendar, "month": item.source_month,
                     "day": item.source_day, "end_month": item.source_end_month,
                     "end_day": item.source_end_day}
                    if item.source_calendar is not None else None
                ),
                "profile_id": item.profile_id,
                "projection_status": (
                    PROFILE_STATUS
                    if item.jurisdiction in {"sacred", "sacred-marker"}
                    else "declared-common-observance"
                ),
            }
            for item in observances_for_ordinal(day.ordinal)
        ],
        "jubilee": {
            "configuration": {
                "epoch_common_year": configuration.epoch_common_year,
                "epoch_cycle": configuration.epoch_cycle,
                "rollover_rule": configuration.rollover_rule,
                "selection_source": (
                    "explicit-call-configuration"
                    if jubilee_configuration is not None
                    else "declared-project-profile"
                ),
                "authority_scope": "calculation-inputs-only",
                "decision_status": (
                    PROFILE_STATUS
                    if jubilee_configuration is None
                    else "explicit-comparison-input-not-author-selected"
                ),
                "selected_policy_applies": jubilee_configuration is None,
            },
            "designation_status": (
                "unconfigured-epoch"
                if configuration.epoch_common_year is None
                else "before-epoch"
                if day.year < configuration.epoch_common_year
                else "computed-under-stated-configuration"
            ),
            "release_day_projection_status": (
                PROFILE_STATUS
                if jubilee_configuration is None
                else "computed-under-explicit-comparison-not-author-selected"
            ),
            "proclamation_ordinal_year": cycle_state.proclamation_ordinal_year if cycle_state else None,
            "completed_cycle": cycle_state.completed_cycle if cycle_state else None,
            "cycle": day.jubilee_cycle,
            "year": day.jubilee_year,
            "seven_year": {
                "block": (
                    ((day.jubilee_year - 1) // 7) + 1
                    if day.jubilee_year is not None and day.jubilee_year <= 49
                    else None
                ),
                "year_in_block": (
                    ((day.jubilee_year - 1) % 7) + 1
                    if day.jubilee_year is not None and day.jubilee_year <= 49
                    else None
                ),
                "is_seventh_year": day.is_sabbatical_threshold,
            },
            "forty_nine": {
                "year": (
                    day.jubilee_year
                    if day.jubilee_year is not None and day.jubilee_year <= 49
                    else None
                ),
                "is_year_49": day.jubilee_year == 49,
                "completed": day.is_jubilee_year,
            },
            "is_sabbatical_threshold": day.is_sabbatical_threshold,
            "is_jubilee_year": day.is_jubilee_year,
            "is_jubilee_release_day": day.is_jubilee_release_day,
        },
        "long_cycle_comparison": compare_long_cycles(
            common_year=day.year,
            epoch_common_year=configuration.epoch_common_year,
            epoch_cycle=configuration.epoch_cycle,
        ),
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
