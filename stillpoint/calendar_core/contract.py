from __future__ import annotations

"""Legacy aggregate artifact.

New consumers MUST use calendar_core_spec.json plus
calendar_projection_vectors.json and a finite calendar_publication.json.
This module remains only to give stacked clients an explicit migration path.
"""

import json
from pathlib import Path
from typing import Any

from .spec import SPEC_VERSION, build_calendar_core_spec
from .vectors import (
    VECTORS_VERSION,
    build_calendar_projection_vectors,
)

CONTRACT_VERSION = "stillpoint-calendar-core-contract-v1-legacy"


def build_calendar_core_contract() -> dict[str, Any]:
    spec = build_calendar_core_spec()
    vectors = build_calendar_projection_vectors()
    ordinary = spec["ordinaryYear"]
    spring = spec["supportedPublicationRules"]["v3.3-candidate"]["springGate"]

    return {
        "version": CONTRACT_VERSION,
        "deprecated": True,
        "replacementArtifacts": [
            "calendar_core_spec.json",
            "calendar_publication.json",
            "calendar_projection_vectors.json",
        ],
        "specVersion": SPEC_VERSION,
        "vectorsVersion": VECTORS_VERSION,
        "jurisdiction": spec["jurisdiction"],
        "constants": {
            "apparentHorizonZenithDegrees": spec["boundaryConvention"][
                "apparentHorizonZenithDegrees"
            ],
            "baseYearDays": ordinary["days"],
            "monthLengths": ordinary["monthLengths"],
            "phaseLengths": ordinary["phaseLengths"],
            "gateSequence": ordinary["gateSequence"],
            "reconciliationDaysAllowed": spec["namespaces"]["reconciliation"][
                "allowedDays"
            ],
            "springGateOrdinalV33Candidate": spring["ordinal"],
        },
        "conformanceContext": vectors["conformanceContext"],
        "goldenVectors": vectors["vectors"],
    }


def export_calendar_core_contract(path: Path) -> None:
    path.write_text(
        json.dumps(build_calendar_core_contract(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
