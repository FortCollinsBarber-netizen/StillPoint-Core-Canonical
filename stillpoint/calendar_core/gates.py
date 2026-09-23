from __future__ import annotations

from .governor import (
    RHYTHM_GOVERNOR,
    RhythmAuthority,
    RhythmRequest,
)
from .models import EnochPhase

PHASE_LENGTHS = (30, 30, 31) * 4
GATE_SEQUENCE = (4, 5, 6, 6, 5, 4, 3, 2, 1, 1, 2, 3)
MOTIONS = (
    "northward",
    "northward",
    "northward_to_turn",
    "southward_from_turn",
    "southward",
    "southward",
    "southward",
    "southward",
    "southward_to_turn",
    "northward_from_turn",
    "northward",
    "northward",
)


def validate_gate_model() -> None:
    if PHASE_LENGTHS != (30, 30, 31) * 4:
        raise RuntimeError("phase lengths were mutated")
    if sum(PHASE_LENGTHS) != 364:
        raise RuntimeError("twelve phases must total 364 days")
    if GATE_SEQUENCE != (4, 5, 6, 6, 5, 4, 3, 2, 1, 1, 2, 3):
        raise RuntimeError("only the six-paired-gate / twelve-phase model is valid")
    if set(GATE_SEQUENCE) != {1, 2, 3, 4, 5, 6}:
        raise RuntimeError("gate geometry must contain exactly six paired gates")


def phase_for_base_day(day_number: int) -> EnochPhase:
    RHYTHM_GOVERNOR.require(
        RhythmRequest(
            authority=RhythmAuthority.OVERLAY,
            source="seasonal-enochic-gates",
            annotation={"ordinal": day_number},
        )
    )
    validate_gate_model()
    if not 1 <= day_number <= 364:
        raise ValueError("base year day must be within 1..364")

    start = 1
    for index, length in enumerate(PHASE_LENGTHS):
        end = start + length - 1
        if start <= day_number <= end:
            return EnochPhase(
                phase=index + 1,
                gate=GATE_SEQUENCE[index],
                motion=MOTIONS[index],
                days=length,
                start_ordinal=start,
                end_ordinal=end,
            )
        start = end + 1
    raise AssertionError("unreachable")
