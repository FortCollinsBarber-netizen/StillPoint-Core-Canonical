from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .astronomy import AstronomyEvidence
from .governor import (
    RHYTHM_GOVERNOR,
    RhythmAuthority,
    RhythmRequest,
)


class WitnessValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _validate_digest(value: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdefABCDEF" for ch in value)
    ):
        raise WitnessValidationError(
            "INVALID_WITNESS_DIGEST",
            "witness SHA-256 must be 64 hexadecimal characters",
        )


def _validate_instant(value: datetime) -> None:
    if value.tzinfo is None:
        raise WitnessValidationError(
            "NAIVE_WITNESS_INSTANT",
            "witness instant must be timezone-aware",
        )


@dataclass(frozen=True)
class LunarWitness:
    """Evidence-only lunar observation.

    This object has no API for mutating Calendar Core law, month lengths,
    appointed times, year openings, or Reconciliation.
    """

    phase: str
    instant_utc: datetime
    source_id: str
    evidence_sha256: str
    reference_id: str | None = None

    def __post_init__(self) -> None:
        if self.phase not in {
            "new",
            "first_quarter",
            "full",
            "last_quarter",
        }:
            raise WitnessValidationError(
                "UNSUPPORTED_LUNAR_PHASE",
                f"unsupported lunar phase: {self.phase!r}",
            )
        _validate_instant(self.instant_utc)
        if not self.source_id.strip():
            raise WitnessValidationError(
                "MISSING_WITNESS_SOURCE",
                "lunar witness source_id is required",
            )
        _validate_digest(self.evidence_sha256)
        RHYTHM_GOVERNOR.require(
            RhythmRequest(
                authority=RhythmAuthority.OBSERVE,
                source=f"lunar-witness:{self.source_id}",
                annotation={
                    "phase": self.phase,
                    "reference_id": self.reference_id,
                },
            )
        )


@dataclass(frozen=True)
class SeasonGateWitness:
    """Bounded solar/season evidence with explicit frame and direction."""

    event: str
    year: int
    instant_utc: datetime
    source_id: str
    evidence_sha256: str
    reference_frame: str
    gate_position: int | None
    direction_of_travel: str

    def __post_init__(self) -> None:
        _validate_instant(self.instant_utc)
        if not self.source_id.strip():
            raise WitnessValidationError(
                "MISSING_WITNESS_SOURCE",
                "season/gate witness source_id is required",
            )
        _validate_digest(self.evidence_sha256)
        if not self.reference_frame.strip():
            raise WitnessValidationError(
                "MISSING_REFERENCE_FRAME",
                "season/gate witness reference_frame is required",
            )
        if self.gate_position is not None and not 1 <= self.gate_position <= 6:
            raise WitnessValidationError(
                "INVALID_GATE_POSITION",
                "gate_position must be within 1..6 when supplied",
            )
        if self.direction_of_travel not in {
            "northward",
            "southward",
            "turning",
            "not-applicable",
        }:
            raise WitnessValidationError(
                "INVALID_GATE_DIRECTION",
                "direction_of_travel is not recognized",
            )
        RHYTHM_GOVERNOR.require(
            RhythmRequest(
                authority=RhythmAuthority.OBSERVE,
                source=f"season-gate-witness:{self.source_id}",
                annotation={
                    "event": self.event,
                    "reference_frame": self.reference_frame,
                    "gate_position": self.gate_position,
                    "direction_of_travel": self.direction_of_travel,
                },
            )
        )


def as_march_equinox_evidence(
    witness: SeasonGateWitness,
) -> AstronomyEvidence:
    """Explicitly bridge one seasonal witness into the reference-rule API.

    The conversion does not invoke a reference rule and therefore cannot choose
    Reconciliation by itself.
    """
    if witness.event != "march_equinox":
        raise WitnessValidationError(
            "WITNESS_NOT_MARCH_EQUINOX",
            "only March-equinox evidence can enter the Spring Gate reference rule",
        )
    return AstronomyEvidence(
        event="march_equinox",
        year=witness.year,
        instant_utc=witness.instant_utc,
        source_id=witness.source_id,
        evidence_sha256=witness.evidence_sha256,
    )
