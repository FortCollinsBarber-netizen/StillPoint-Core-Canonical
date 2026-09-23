"""Clock OS: read-only temporal runtime over the enacted Common Calendar.

Clock OS translates between civil instants and the immutable Calendar Core
surface. Solar boundaries determine when a named day opens at a supplied
location; they never alter the 364-day grid, weekday pattern, or publication.
No location is embedded in this module. Enactment-specific location and
standard-time settings are supplied by the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .calendar_core.models import GeoPoint
from .calendar_core.runtime_surface import (
    calendar_day_payload,
    load_enacted_publication,
)
from .calendar_core.sunset import apparent_sunset_utc, bracket_sunset
from .calendar_core.week import protected_time_state
from .lunar import lunar_phase_witness


CLOCK_SCHEMA = "stillpoint.clock-os.v1"
CLOCK_AUTHORITY = "read-only-temporal-projection"


@dataclass(frozen=True)
class ClockConfig:
    location: GeoPoint
    local_zone: str
    common_standard_offset_seconds: int
    publication_path: Path | str | None = None

    def __post_init__(self) -> None:
        # Resolve the zone eagerly so invalid enactment data fails closed.
        ZoneInfo(self.local_zone)
        if not -86_400 < int(self.common_standard_offset_seconds) < 86_400:
            raise ValueError("common_standard_offset_seconds must be within one day")


def _publication_position(
    boundary_civil_date: date,
    document: dict[str, Any],
) -> tuple[int, int] | None:
    for row in document["years"]:
        opening = date.fromisoformat(str(row["openingCivilDate"]))
        offset = (boundary_civil_date - opening).days
        if 0 <= offset < 364:
            return int(row["year"]), offset + 1
    return None


def _next_calendar_day(
    year: int,
    ordinal: int,
    *,
    publication_path: Path | str | None,
) -> dict[str, Any] | None:
    if ordinal < 364:
        next_year, next_ordinal = year, ordinal + 1
    else:
        next_year, next_ordinal = year + 1, 1
    try:
        return calendar_day_payload(
            next_year,
            next_ordinal,
            publication_path=publication_path,
        )
    except ValueError:
        return None


def canonical_civil_window(
    year: int,
    ordinal: int,
    *,
    config: ClockConfig,
) -> dict[str, Any]:
    """Return the location-specific sunset window for one canonical address."""

    day = calendar_day_payload(
        int(year),
        int(ordinal),
        publication_path=config.publication_path,
    )
    opens_on = date.fromisoformat(day["civil_window"]["opens"])
    closes_on = date.fromisoformat(day["civil_window"]["closes"])
    opens_at = apparent_sunset_utc(opens_on, config.location)
    closes_at = apparent_sunset_utc(closes_on, config.location)
    return {
        "schema": CLOCK_SCHEMA,
        "authority": CLOCK_AUTHORITY,
        "calendar_address": day["calendar_address"],
        "canonical_coordinate": day["canonical_coordinate"],
        "interop": {
            "calendar": "proleptic-gregorian",
            "role": "translation-only",
            "opening_date": opens_on.isoformat(),
            "closing_date": closes_on.isoformat(),
            "mutates_calendar": False,
        },
        # Compatibility names for existing consumers. These are interoperability
        # dates, not Common Calendar named-date authority.
        "opening_civil_date": opens_on.isoformat(),
        "closing_civil_date": closes_on.isoformat(),
        "opens_at_utc": opens_at.isoformat(),
        "closes_at_utc": closes_at.isoformat(),
        "location_id": config.location.id,
        "boundary_protocol": "apparent-sunrise-set-0.8333",
        "calendar_publication": day["publication"],
    }


def address_for_instant(
    instant: datetime,
    *,
    config: ClockConfig,
) -> str | None:
    """Resolve one aware instant to the enacted canonical address."""

    snapshot = clock_snapshot(instant, config=config)
    current = snapshot["calendar"]
    return None if current is None else str(current["calendar_address"])


def clock_snapshot(
    instant: datetime,
    *,
    config: ClockConfig,
) -> dict[str, Any]:
    """Project an instant into Clock OS without mutating Calendar law or state."""

    if instant.tzinfo is None:
        raise ValueError("instant must be timezone-aware")

    document = load_enacted_publication(config.publication_path)
    instant_utc = instant.astimezone(timezone.utc)
    civil_timestamp = instant_utc.astimezone(ZoneInfo(config.local_zone))
    common_zone = timezone(
        timedelta(seconds=int(config.common_standard_offset_seconds))
    )
    common_timestamp = instant_utc.astimezone(common_zone)

    pair = bracket_sunset(
        instant_utc,
        config.location,
        config.local_zone,
    )
    weekly = protected_time_state(
        instant_utc,
        location=config.location,
        local_zone=config.local_zone,
    )
    position = _publication_position(pair.previous_civil_date, document)

    current: dict[str, Any] | None = None
    following: dict[str, Any] | None = None
    if position is not None:
        year, ordinal = position
        current = calendar_day_payload(
            year,
            ordinal,
            publication_path=config.publication_path,
        )
        following = _next_calendar_day(
            year,
            ordinal,
            publication_path=config.publication_path,
        )

    authority = document["authority"]
    rows = document["years"]
    next_begins: dict[str, Any] | None = None
    if following is not None:
        next_begins = {
            "calendar_address": following["calendar_address"],
            "common_date": following["common_date"],
            "observances": following["observances"],
            "season": following["season"],
            "jubilee": following["jubilee"],
        }

    return {
        "schema": CLOCK_SCHEMA,
        "authority": CLOCK_AUTHORITY,
        "instant": {
            "utc": instant_utc.isoformat(),
            "civil": civil_timestamp.isoformat(),
            "local_zone": config.local_zone,
            "common_standard": common_timestamp.isoformat(),
            "common_standard_offset_seconds": int(
                config.common_standard_offset_seconds
            ),
            "common_clock": common_timestamp.strftime("%H:%M:%S"),
        },
        "location": {
            "id": config.location.id,
            "coordinate_system": "WGS84",
            "latitude": config.location.latitude,
            "longitude": config.location.longitude,
        },
        "lunar_witness": lunar_phase_witness(instant_utc),
        "calendar_state": "ORDINARY" if current is not None else "OUTSIDE_RANGE",
        "calendar": current,
        "protected_time": {
            "named_day": weekly.named_day,
            "is_sabbath": weekly.is_sabbath,
            "is_lords_day": weekly.is_lords_day,
            "is_stillpoint": weekly.is_stillpoint,
        },
        "boundaries": {
            "current_day_opened_at": pair.previous.isoformat(),
            "current_day_closes_at": pair.next.isoformat(),
            "opening_civil_date": pair.previous_civil_date.isoformat(),
            "closing_civil_date": pair.next_civil_date.isoformat(),
            "next_protected_boundary": (
                weekly.next_protected_boundary.isoformat()
                if weekly.next_protected_boundary is not None
                else None
            ),
            "next_protected_boundary_label": weekly.next_protected_boundary_label,
            "next_begins": next_begins,
        },
        "publication": {
            "version": document["publicationVersion"],
            "digest": document["publicationDigest"],
            "authority_id": authority["id"],
            "authority_status": authority["status"],
            "first_year": int(rows[0]["year"]),
            "last_year": int(rows[-1]["year"]),
            "year_count": len(rows),
            "total_days": len(rows) * 364,
        },
        "invariants": {
            "year_days": 364,
            "weeks_per_year": 52,
            "december_31_exists": False,
            "astronomy_mutates_grid": False,
            "lunar_witness_mutates_grid": False,
            "location_is_enactment_input_not_calendar_law": True,
            "interop_calendar_is_translation_only": True,
            "coordinate_observation_interpretation_separated": True,
        },
    }
