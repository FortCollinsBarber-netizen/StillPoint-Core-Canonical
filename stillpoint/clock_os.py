"""Clock OS: read-only temporal runtime over the enacted Common Calendar.

Clock OS translates between civil instants and the immutable Calendar Core
surface. The familiar 24-hour coordination clock remains intact. The Common
Calendar date changes at midnight in the enacted fixed standard offset, so DST
cannot move the date boundary. Local solar boundaries independently govern
creation-facing Sabbath / StillPoint state. Neither astronomy nor clock policy
may alter the 364-day grid, weekday pattern, or publication.

No location is embedded in this module. Enactment-specific location and
standard-time settings are supplied by the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .calendar_core.governor import RHYTHM_GOVERNOR, RhythmAuthority, RhythmRequest
from .calendar_core.models import DuskProtocol, GeoPoint
from .calendar_core.governor import (
    RHYTHM_GOVERNOR,
    RhythmAuthority,
    RhythmRequest,
)
from .calendar_core.runtime_surface import (
    calendar_day_payload,
    load_enacted_publication,
)
from .calendar_core.sunset import (
    apparent_sunrise_utc,
    apparent_sunset_utc,
    bracket_sunset,
    solar_event_utc,
)
from .calendar_core.week import protected_time_state_for_common_date
from .lunar import lunar_phase_witness


CLOCK_SCHEMA = "stillpoint.clock-os.v1"
CLOCK_AUTHORITY = "read-only-temporal-projection"
CIVIL_TWILIGHT_PROTOCOL = DuskProtocol(
    id="civil-twilight-6deg",
    zenith_degrees=96.0,
)


def _governed_calendar_day(
    year: int,
    ordinal: int,
    *,
    publication_path: Path | str | None,
) -> dict[str, Any]:
    RHYTHM_GOVERNOR.require(
        RhythmRequest(
            RhythmAuthority.READ,
            "clock-os",
        )
    )
    return calendar_day_payload(
        int(year),
        int(ordinal),
        publication_path=publication_path,
    )


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
        return _governed_calendar_day(
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
    """Return the fixed-standard 24-hour coordination window.

    The external projection date is an interoperability bridge only. Local
    solar events are observation data and cannot redefine the canonical date.
    """

    RHYTHM_GOVERNOR.require(
        RhythmRequest(
            authority=RhythmAuthority.COORDINATE,
            source="clock-os",
            annotation={"common_standard_uses_dst": False},
        )
    )
    day = _governed_calendar_day(
        int(year),
        int(ordinal),
        publication_path=config.publication_path,
    )
    projection_date = date.fromisoformat(day["civil_window"]["opens"])
    standard_zone = timezone(
        timedelta(seconds=int(config.common_standard_offset_seconds))
    )
    opens_standard = datetime.combine(
        projection_date,
        time.min,
        tzinfo=standard_zone,
    )
    closes_standard = opens_standard + timedelta(days=1)
    sunset = apparent_sunset_utc(projection_date, config.location)
    next_sunset = apparent_sunset_utc(
        projection_date + timedelta(days=1),
        config.location,
    )
    return {
        "schema": CLOCK_SCHEMA,
        "authority": CLOCK_AUTHORITY,
        "calendar_address": day["calendar_address"],
        "common_civil_coordinate": day["common_civil_coordinate"],
        "boundary": "common-standard-midnight",
        "opens_at_common_standard": opens_standard.isoformat(),
        "closes_at_common_standard": closes_standard.isoformat(),
        "opens_at_utc": opens_standard.astimezone(timezone.utc).isoformat(),
        "closes_at_utc": closes_standard.astimezone(timezone.utc).isoformat(),
        "interop": {
            "frame": day["civil_window"]["frame"],
            "role": day["civil_window"]["role"],
            "grid_authority": day["civil_window"]["grid_authority"],
            "projection_date": projection_date.isoformat(),
        },
        "solar_witness": {
            "sunset_utc": sunset.isoformat(),
            "next_sunset_utc": next_sunset.isoformat(),
            "calendar_effect": "none",
        },
        "location_id": config.location.id,
        "calendar_publication": day["publication"],
    }


def _local_light_witness(
    instant_utc: datetime,
    *,
    projection_date: date,
    location: GeoPoint,
) -> dict[str, Any]:
    dawn = solar_event_utc(
        projection_date,
        location,
        rising=True,
        protocol=CIVIL_TWILIGHT_PROTOCOL,
    )
    sunrise = apparent_sunrise_utc(projection_date, location)
    sunset = apparent_sunset_utc(projection_date, location)
    dusk = solar_event_utc(
        projection_date,
        location,
        rising=False,
        protocol=CIVIL_TWILIGHT_PROTOCOL,
    )

    if instant_utc < dawn:
        phase = "DARKNESS"
        next_event, next_at = "CIVIL_DAWN", dawn
    elif instant_utc < sunrise:
        phase = "DAWN"
        next_event, next_at = "SUNRISE", sunrise
    elif instant_utc < sunset:
        phase = "DAYLIGHT"
        next_event, next_at = "SUNSET", sunset
    elif instant_utc < dusk:
        phase = "DUSK"
        next_event, next_at = "DARKNESS", dusk
    else:
        phase = "DARKNESS"
        next_dawn = solar_event_utc(
            projection_date + timedelta(days=1),
            location,
            rising=True,
            protocol=CIVIL_TWILIGHT_PROTOCOL,
        )
        next_event, next_at = "CIVIL_DAWN", next_dawn

    return {
        "schema": "stillpoint.local-light.v1",
        "authority": "observation-only",
        "projection_date": projection_date.isoformat(),
        "phase": phase,
        "civil_dawn_utc": dawn.isoformat(),
        "sunrise_utc": sunrise.isoformat(),
        "sunset_utc": sunset.isoformat(),
        "civil_dusk_utc": dusk.isoformat(),
        "next_event": next_event,
        "next_event_utc": next_at.isoformat(),
        "calendar_effect": "none",
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

    RHYTHM_GOVERNOR.require(
        RhythmRequest(
            authority=RhythmAuthority.COORDINATE,
            source="clock-os",
        )
    )
    RHYTHM_GOVERNOR.require(
        RhythmRequest(
            authority=RhythmAuthority.OBSERVE,
            source="clock-os-solar-lunar-observation",
            annotation={
                "solar_boundaries": True,
                "lunar_witness": True,
            },
        )
    )

    document = load_enacted_publication(config.publication_path)
    instant_utc = instant.astimezone(timezone.utc)
    civil_timestamp = instant_utc.astimezone(ZoneInfo(config.local_zone))
    common_zone = timezone(
        timedelta(seconds=int(config.common_standard_offset_seconds))
    )
    common_timestamp = instant_utc.astimezone(common_zone)
    RHYTHM_GOVERNOR.require(
        RhythmRequest(
            RhythmAuthority.COORDINATE,
            "clock-os",
            clock_time=common_timestamp.strftime("%H:%M:%S"),
        )
    )
    RHYTHM_GOVERNOR.require(
        RhythmRequest(
            RhythmAuthority.OBSERVE,
            "clock-os-witnesses",
            annotation={
                "local_light": True,
                "lunar_witness": True,
            },
        )
    )

    pair = bracket_sunset(
        instant_utc,
        config.location,
        config.local_zone,
    )
    # Calendar labels belong to the fixed 24-hour coordination layer.
    # Sunset has jurisdiction over protected/creation-facing time, not over
    # the named Common Calendar date itself.
    position = _publication_position(common_timestamp.date(), document)

    current: dict[str, Any] | None = None
    following: dict[str, Any] | None = None
    weekly = None
    local_light = _local_light_witness(
        instant_utc,
        projection_date=common_timestamp.date(),
        location=config.location,
    )
    if position is not None:
        year, ordinal = position
        current = _governed_calendar_day(
            year,
            ordinal,
            publication_path=config.publication_path,
        )
        following = _next_calendar_day(
            year,
            ordinal,
            publication_path=config.publication_path,
        )
        weekly = protected_time_state_for_common_date(
            instant_utc,
            common_weekday=str(current["common_date"]["weekday"]),
            projection_date=common_timestamp.date(),
            location=config.location,
        )

    common_calendar_coordinate: dict[str, Any] | None = None
    if current is not None:
        common_date_value = current["common_date"]
        common_time = common_timestamp.strftime("%H:%M:%S")
        common_calendar_coordinate = {
            "year": int(common_date_value["year"]),
            "month": int(common_date_value["month"]),
            "day": int(common_date_value["day"]),
            "weekday": str(common_date_value["weekday"]),
            "time": common_time,
            "display": (
                f"{int(common_date_value['year']):04d}-"
                f"{int(common_date_value['month']):02d}-"
                f"{int(common_date_value['day']):02d} "
                f"{common_time}"
            ),
            "calendar_address": current["calendar_address"],
        }

    authority = document["authority"]
    rows = document["years"]
    next_common_midnight = datetime.combine(
        common_timestamp.date() + timedelta(days=1),
        datetime.min.time(),
        tzinfo=common_zone,
    )
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
            "common_calendar": common_calendar_coordinate,
        },
        "location": {
            "id": config.location.id,
            "coordinate_system": "WGS84",
            "latitude": config.location.latitude,
            "longitude": config.location.longitude,
        },
        "lunar_witness": lunar_phase_witness(instant_utc),
        "local_light": local_light,
        "calendar_state": "ORDINARY" if current is not None else "OUTSIDE_RANGE",
        "calendar": current,
        "protected_time": (
            {
                "named_day": weekly.named_day,
                "is_sabbath": weekly.is_sabbath,
                "is_lords_day": weekly.is_lords_day,
                "is_stillpoint": weekly.is_stillpoint,
            }
            if weekly is not None
            else None
        ),
        "boundaries": {
            "coordination_date_source": "fixed-standard-midnight",
            "coordination_date": common_timestamp.date().isoformat(),
            "next_coordination_midnight": next_common_midnight.isoformat(),
            "creation_day_opened_at": pair.previous.isoformat(),
            "creation_day_closes_at": pair.next.isoformat(),
            # Compatibility aliases retained for existing clients.
            "current_day_opened_at": pair.previous.isoformat(),
            "current_day_closes_at": pair.next.isoformat(),
            "opening_civil_date": pair.previous_civil_date.isoformat(),
            "closing_civil_date": pair.next_civil_date.isoformat(),
            "next_protected_boundary": (
                weekly.next_protected_boundary.isoformat()
                if weekly is not None
                and weekly.next_protected_boundary is not None
                else None
            ),
            "next_protected_boundary_label": (
                weekly.next_protected_boundary_label
                if weekly is not None
                else None
            ),
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
            "february_29_exists": False,
            "coordination_clock": "24-hour",
            "coordination_date_boundary": "fixed-standard-midnight",
            "common_standard_uses_dst": False,
            "protected_time_boundary": "local-apparent-sunset",
            "astronomy_mutates_grid": False,
            "lunar_witness_mutates_grid": False,
            "location_is_enactment_input_not_calendar_law": True,
            "calendar_date_changes_at_common_standard_midnight": True,
            "solar_boundary_mutates_calendar_date": False,
            "daylight_saving_mutates_common_clock": False,
            "interop_calendar_is_translation_only": True,
            "rhythm_governor_enforced": True,
            "overlay_rule": "inhabit-the-surface-never-rewrite-the-surface",
        },
    }
