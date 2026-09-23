from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable

from .governor import (
    RHYTHM_GOVERNOR,
    RhythmAuthority,
    RhythmRequest,
)


OVERLAY_SCHEMA = "stillpoint.external-calendar-witness.v1"
EXTERNAL_WITNESS_ARTIFACT_VERSION = "stillpoint-external-calendar-witnesses-v1"


@dataclass(frozen=True)
class ExternalCalendarWitness:
    """One external-calendar observation attached to an interoperability date.

    These records are evidence/overlays only. They never choose a Common
    Calendar address, insert a day, change a weekday, move an observance, or
    alter the enacted 364-day / 50-year surface.
    """

    id: str
    name: str
    source_calendar: str
    external_date: date
    begins_at: str = "date"
    source_refs: tuple[str, ...] = ()
    qualification: str | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("external witness id must be non-empty")
        if not self.name.strip():
            raise ValueError("external witness name must be non-empty")
        if self.source_calendar not in {"jewish", "islamic"}:
            raise ValueError(
                "source_calendar must be 'jewish' or 'islamic'"
            )
        if self.begins_at not in {"date", "sunset"}:
            raise ValueError("begins_at must be 'date' or 'sunset'")
        if not self.source_refs:
            raise ValueError("external witness requires source provenance")

        RHYTHM_GOVERNOR.require(
            RhythmRequest(
                authority=RhythmAuthority.OBSERVE,
                source=f"external-calendar-witness:{self.source_calendar}",
                annotation={
                    "witness_id": self.id,
                    "external_date": self.external_date.isoformat(),
                    "begins_at": self.begins_at,
                },
            )
        )

    def as_payload(self) -> dict:
        decision = RHYTHM_GOVERNOR.require(
            RhythmRequest(
                authority=RhythmAuthority.OBSERVE,
                source=f"external-calendar-witness:{self.source_calendar}",
                annotation={
                    "witness_id": self.id,
                    "external_date": self.external_date.isoformat(),
                    "begins_at": self.begins_at,
                },
            )
        )
        payload = asdict(self)
        payload["external_date"] = self.external_date.isoformat()
        payload["source_refs"] = list(self.source_refs)
        payload.update(
            {
                "schema": OVERLAY_SCHEMA,
                "authority": "witness-only",
                "grid_authority": False,
                "calendar_effect": "none",
                "rhythm_governor": {
                    "authority": decision.authority.value,
                    "decision": decision.code,
                    "surface_mutated": decision.surface_mutated,
                },
            }
        )
        return payload


# Seed-year external witnesses. These preserve what the external calendars
# report for 2026 so the fixed Common Calendar can compare rather than absorb
# them. They are intentionally not repeated into later Common years.
JEWISH_2026: tuple[ExternalCalendarWitness, ...] = (
    ExternalCalendarWitness(
        "jewish-purim-2026",
        "Purim begins",
        "jewish",
        date(2026, 3, 2),
        begins_at="sunset",
        source_refs=("Hebcal 2026 Jewish calendar",),
    ),
    ExternalCalendarWitness(
        "jewish-passover-2026",
        "Passover begins",
        "jewish",
        date(2026, 4, 1),
        begins_at="sunset",
        source_refs=("Hebcal 2026 Jewish calendar",),
    ),
    ExternalCalendarWitness(
        "jewish-shavuot-2026",
        "Shavuot begins",
        "jewish",
        date(2026, 5, 21),
        begins_at="sunset",
        source_refs=("Hebcal 2026 Jewish calendar",),
    ),
    ExternalCalendarWitness(
        "jewish-tisha-bav-2026",
        "Tisha B'Av begins",
        "jewish",
        date(2026, 7, 22),
        begins_at="sunset",
        source_refs=("Hebcal 2026 Jewish calendar",),
    ),
    ExternalCalendarWitness(
        "jewish-rosh-hashanah-2026",
        "Rosh Hashanah begins",
        "jewish",
        date(2026, 9, 11),
        begins_at="sunset",
        source_refs=("Hebcal 2026 Jewish calendar",),
    ),
    ExternalCalendarWitness(
        "jewish-yom-kippur-2026",
        "Yom Kippur begins",
        "jewish",
        date(2026, 9, 20),
        begins_at="sunset",
        source_refs=("Hebcal 2026 Jewish calendar",),
    ),
    ExternalCalendarWitness(
        "jewish-sukkot-2026",
        "Sukkot begins",
        "jewish",
        date(2026, 9, 25),
        begins_at="sunset",
        source_refs=("Hebcal 2026 Jewish calendar",),
    ),
    ExternalCalendarWitness(
        "jewish-shemini-atzeret-2026",
        "Shemini Atzeret begins",
        "jewish",
        date(2026, 10, 2),
        begins_at="sunset",
        source_refs=("Hebcal 2026 Jewish calendar",),
    ),
    ExternalCalendarWitness(
        "jewish-simchat-torah-2026",
        "Simchat Torah begins",
        "jewish",
        date(2026, 10, 3),
        begins_at="sunset",
        source_refs=("Hebcal 2026 Jewish calendar",),
    ),
    ExternalCalendarWitness(
        "jewish-hanukkah-2026",
        "Hanukkah begins",
        "jewish",
        date(2026, 12, 4),
        begins_at="sunset",
        source_refs=("Hebcal 2026 Jewish calendar",),
    ),
)


ISLAMIC_2026: tuple[ExternalCalendarWitness, ...] = (
    ExternalCalendarWitness(
        "islamic-ramadan-begins-2026",
        "Ramadan begins",
        "islamic",
        date(2026, 2, 17),
        begins_at="sunset",
        source_refs=("2026 external Islamic calendar witness",),
        qualification="Actual month opening may differ by community/crescent sighting.",
    ),
    ExternalCalendarWitness(
        "islamic-first-fast-2026",
        "First fasting day of Ramadan",
        "islamic",
        date(2026, 2, 18),
        source_refs=("2026 external Islamic calendar witness",),
        qualification="Actual month opening may differ by community/crescent sighting.",
    ),
    ExternalCalendarWitness(
        "islamic-eid-al-fitr-2026",
        "Eid al-Fitr",
        "islamic",
        date(2026, 3, 20),
        source_refs=("2026 external Islamic calendar witness",),
        qualification="Date may differ by community/crescent sighting.",
    ),
    ExternalCalendarWitness(
        "islamic-dhul-hijjah-2026",
        "Dhul Hijjah begins",
        "islamic",
        date(2026, 5, 18),
        source_refs=("2026 external Islamic calendar witness",),
        qualification="Actual month opening may differ by community/crescent sighting.",
    ),
    ExternalCalendarWitness(
        "islamic-arafah-2026",
        "Day of Arafah",
        "islamic",
        date(2026, 5, 26),
        source_refs=("2026 external Islamic calendar witness",),
        qualification="Date may differ by community/crescent sighting.",
    ),
    ExternalCalendarWitness(
        "islamic-eid-al-adha-2026",
        "Eid al-Adha",
        "islamic",
        date(2026, 5, 27),
        source_refs=("2026 external Islamic calendar witness",),
        qualification="Date may differ by community/crescent sighting.",
    ),
    ExternalCalendarWitness(
        "islamic-new-year-2026",
        "Islamic New Year / Muharram begins",
        "islamic",
        date(2026, 6, 16),
        source_refs=("2026 external Islamic calendar witness",),
        qualification="Actual month opening may differ by community/crescent sighting.",
    ),
    ExternalCalendarWitness(
        "islamic-ashura-2026",
        "Ashura",
        "islamic",
        date(2026, 6, 25),
        source_refs=("2026 external Islamic calendar witness",),
        qualification="Date may differ by community/crescent sighting.",
    ),
)


ALL_EXTERNAL_WITNESSES: tuple[ExternalCalendarWitness, ...] = (
    JEWISH_2026 + ISLAMIC_2026
)


def witnesses_for_external_date(
    external_date: date,
    *,
    calendars: Iterable[str] | None = None,
) -> tuple[ExternalCalendarWitness, ...]:
    RHYTHM_GOVERNOR.require(
        RhythmRequest(
            authority=RhythmAuthority.READ,
            source="external-calendar-witness-catalog",
        )
    )
    allowed = None if calendars is None else {str(value).lower() for value in calendars}
    if allowed is not None:
        unsupported = allowed - {"jewish", "islamic"}
        if unsupported:
            raise ValueError(
                "unsupported external witness calendar(s): "
                + ", ".join(sorted(unsupported))
            )
    return tuple(
        event
        for event in ALL_EXTERNAL_WITNESSES
        if event.external_date == external_date
        and (allowed is None or event.source_calendar.lower() in allowed)
    )



def build_external_witness_artifact() -> dict[str, Any]:
    RHYTHM_GOVERNOR.require(
        RhythmRequest(
            authority=RhythmAuthority.READ,
            source="external-calendar-witness-artifact",
        )
    )
    return {
        "version": EXTERNAL_WITNESS_ARTIFACT_VERSION,
        "authorityStatus": "witness-layer-no-grid-authority",
        "jurisdiction": {
            "gridAuthority": False,
            "mayInsertDays": False,
            "mayMoveYearOpening": False,
            "mayAlterWeekday": False,
            "mayPromoteExternalCalendarToCommonLaw": False,
        },
        "scope": {
            "externalProjectionYear": 2026,
            "repeatIntoLaterCommonYears": False,
            "role": "comparison-and-observation-only",
        },
        "events": [
            event.as_payload()
            for event in ALL_EXTERNAL_WITNESSES
        ],
        "invariants": [
            "external-calendar-witnesses-never-mutate-common-grid",
            "jewish-calendar-witness-is-not-common-sacred-placement",
            "islamic-calendar-dates-remain-sighting-qualified",
            "seed-witnesses-do-not-repeat-as-calendar-law",
        ],
    }


def export_external_witness_artifact(path: Path) -> None:
    path.write_text(
        json.dumps(
            build_external_witness_artifact(),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
