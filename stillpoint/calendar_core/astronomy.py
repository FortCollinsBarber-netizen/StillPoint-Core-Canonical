from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Protocol


class AstronomyEvidenceError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class AstronomyEvidence:
    """Bounded astronomical evidence supplied to a calendar reference rule."""

    event: str
    year: int
    instant_utc: datetime
    source_id: str
    evidence_sha256: str

    def __post_init__(self) -> None:
        if self.event != "march_equinox":
            raise AstronomyEvidenceError(
                "UNSUPPORTED_ASTRONOMICAL_EVENT",
                f"expected march_equinox evidence; got {self.event!r}",
            )
        if self.instant_utc.tzinfo is None:
            raise AstronomyEvidenceError(
                "NAIVE_ASTRONOMICAL_INSTANT",
                "astronomical evidence instant must be timezone-aware",
            )
        if not isinstance(self.year, int):
            raise AstronomyEvidenceError(
                "INVALID_ASTRONOMICAL_YEAR",
                "astronomical evidence year must be an integer",
            )
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise AstronomyEvidenceError(
                "MISSING_ASTRONOMY_SOURCE",
                "astronomical evidence source_id is required",
            )
        digest = self.evidence_sha256
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(ch not in "0123456789abcdefABCDEF" for ch in digest)
        ):
            raise AstronomyEvidenceError(
                "INVALID_ASTRONOMY_EVIDENCE_DIGEST",
                "astronomical evidence SHA-256 must be 64 hexadecimal characters",
            )


class AstronomyProvider(Protocol):
    """Evidence provider only. It does not choose calendar outcomes."""

    @property
    def provider_id(self) -> str:
        ...

    def march_equinox(self, year: int) -> AstronomyEvidence:
        ...


@dataclass(frozen=True)
class MappingAstronomyProvider:
    """Deterministic provider for supplied, already-custodied evidence."""

    provider_id: str
    evidence_by_year: Mapping[int, AstronomyEvidence]

    def __post_init__(self) -> None:
        if not isinstance(self.provider_id, str) or not self.provider_id.strip():
            raise AstronomyEvidenceError(
                "MISSING_ASTRONOMY_PROVIDER_ID",
                "astronomy provider_id is required",
            )

    def march_equinox(self, year: int) -> AstronomyEvidence:
        try:
            evidence = self.evidence_by_year[year]
        except KeyError as exc:
            raise AstronomyEvidenceError(
                "MISSING_ASTRONOMY_EVIDENCE",
                f"no March equinox evidence is available for {year}",
            ) from exc

        if evidence.year != year:
            raise AstronomyEvidenceError(
                "ASTRONOMY_EVIDENCE_YEAR_MISMATCH",
                f"provider returned evidence for {evidence.year}; expected {year}",
            )
        if evidence.source_id != self.provider_id:
            raise AstronomyEvidenceError(
                "ASTRONOMY_PROVIDER_SOURCE_MISMATCH",
                f"provider {self.provider_id!r} returned evidence from {evidence.source_id!r}",
            )
        return evidence
