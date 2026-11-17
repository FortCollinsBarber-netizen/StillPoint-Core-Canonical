from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .gates import GATE_SEQUENCE, MOTIONS, PHASE_LENGTHS
from .observances import ALL_OBSERVANCES
from .sacred import sacred_profile_payload, long_cycle_policy_payload

POPULATION_ARTIFACT_VERSION = "stillpoint-calendar-population-v2"


def build_calendar_population_artifact() -> dict[str, Any]:
    return {
        "version": POPULATION_ARTIFACT_VERSION,
        "authorityStatus": "population-layer-no-grid-authority",
        "sacredYearProfile": sacred_profile_payload(),
        "longCyclePolicy": long_cycle_policy_payload(),
        "jurisdiction": {
            "gridAuthority": False,
            "mayInsertDays": False,
            "mayMoveYearOpening": False,
            "mayAlterWeekday": False,
        },
        "seasonalArchitecture": {
            "phaseLengths": list(PHASE_LENGTHS),
            "gateSequence": list(GATE_SEQUENCE),
            "motions": list(MOTIONS),
            "quarterDays": 91,
            "sourceRefs": ["1 Enoch 72-82"],
            "authorityRole": "witness-metadata-no-grid-mutation",
        },
        "distributedWitnesses": [
            {
                "id": "torah-appointed-times",
                "sourceRefs": [
                    "Leviticus 23",
                    "Leviticus 25",
                    "Numbers 28-29",
                    "Deuteronomy 16",
                ],
            },
            {
                "id": "enochic-seasonal-architecture",
                "sourceRefs": ["1 Enoch 72-82"],
                "role": "season-gate-witness",
            },
            {
                "id": "jubilees-calendar-witness",
                "sourceRefs": ["Jubilees 6:29-32"],
                "role": "364-day-calendar-witness",
            },
        ],
        "observances": [
            {
                "id": item.id,
                "name": item.name,
                "jurisdiction": item.jurisdiction,
                "month": item.month,
                "day": item.day,
                "endMonth": item.end_month,
                "endDay": item.end_day,
                "assembly": item.assembly,
                "rule": item.rule,
                "sourceRefs": list(item.source_refs),
                "note": item.note,
                "sourceCalendar": item.source_calendar,
                "sourceMonth": item.source_month,
                "sourceDay": item.source_day,
                "sourceEndMonth": item.source_end_month,
                "sourceEndDay": item.source_end_day,
                "profileId": item.profile_id,
            }
            for item in ALL_OBSERVANCES
        ],
        "invariants": [
            "population-never-mutates-grid",
            "source-provenance-remains-attached",
            "observance-addresses-repeat-with-annual-template",
            "astronomy-and-lunar-witnesses-cannot-move-observances",
        ],
    }


def export_calendar_population_artifact(
    path: Path,
) -> None:
    path.write_text(
        json.dumps(
            build_calendar_population_artifact(),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
