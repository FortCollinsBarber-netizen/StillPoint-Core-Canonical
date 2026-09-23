from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .governor import (
    RHYTHM_GOVERNOR,
    RhythmAuthority,
    RhythmRequest,
)


OVERLAY_POLICY_VERSION = "stillpoint-calendar-overlay-policy-v1"

CANONICAL_OVERLAY_KINDS = frozenset({
    "feast",
    "sabbath",
    "stillpoint",
    "seven-year",
    "forty-nine-year",
    "jubilee",
})

WITNESS_OVERLAY_KINDS = frozenset({
    "season",
    "lunar",
    "jewish-calendar",
    "islamic-calendar",
    "local-light",
})

ALL_OVERLAY_KINDS = CANONICAL_OVERLAY_KINDS | WITNESS_OVERLAY_KINDS


@dataclass(frozen=True)
class OverlayRecord:
    kind: str
    id: str
    label: str
    source: str
    data: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.kind not in ALL_OVERLAY_KINDS:
            raise ValueError(f"unsupported calendar overlay kind: {self.kind}")
        if not self.id.strip():
            raise ValueError("overlay id must be non-empty")
        if not self.label.strip():
            raise ValueError("overlay label must be non-empty")
        if not self.source.strip():
            raise ValueError("overlay source must be non-empty")

    @property
    def authority_class(self) -> str:
        if self.kind in CANONICAL_OVERLAY_KINDS:
            return "canonical-overlay"
        return "witness-overlay"

    @property
    def rhythm_authority(self) -> RhythmAuthority:
        if self.kind in WITNESS_OVERLAY_KINDS:
            return RhythmAuthority.OBSERVE
        return RhythmAuthority.OVERLAY

    def as_payload(self) -> dict[str, Any]:
        decision = RHYTHM_GOVERNOR.require(
            RhythmRequest(
                authority=self.rhythm_authority,
                source=f"calendar-overlay:{self.kind}:{self.source}",
                annotation={
                    "overlay_id": self.id,
                    "overlay_kind": self.kind,
                    "authority_class": self.authority_class,
                },
            )
        )
        return {
            "policy_version": OVERLAY_POLICY_VERSION,
            "kind": self.kind,
            "id": self.id,
            "label": self.label,
            "source": self.source,
            "authority_class": self.authority_class,
            "rhythm_governor": {
                "authority": decision.authority.value,
                "decision": decision.code,
                "surface_mutated": decision.surface_mutated,
            },
            "jurisdiction": {
                "grid_authority": False,
                "may_insert_days": False,
                "may_delete_days": False,
                "may_move_named_dates": False,
                "may_change_weekday": False,
                "may_change_year_opening": False,
                "may_change_year_closing": False,
                "may_change_year_length": False,
                "may_create_leap_day": False,
                "may_create_december_31": False,
            },
            "data": deepcopy(dict(self.data)),
        }


def grid_identity(day_payload: Mapping[str, Any]) -> tuple[Any, ...]:
    common = day_payload["common_date"]
    mapping = day_payload["map"]
    return (
        day_payload["calendar_address"],
        common["year"],
        common["month"],
        common["day"],
        common["ordinal"],
        common["week"],
        common["day_in_week"],
        common["weekday"],
        mapping["year_days"],
        mapping["weeks_per_year"],
        mapping["day001_weekday"],
        mapping["first_year"],
        mapping["last_year"],
        mapping["total_days"],
        mapping["december_31_exists"],
    )


def inhabit_surface(
    day_payload: Mapping[str, Any],
    overlays: Iterable[OverlayRecord],
) -> dict[str, Any]:
    """Return a decorated calendar day without granting overlays grid authority."""

    RHYTHM_GOVERNOR.require(
        RhythmRequest(
            authority=RhythmAuthority.READ,
            source="calendar-overlay-surface",
        )
    )
    before = grid_identity(day_payload)
    result = deepcopy(dict(day_payload))
    result["overlays"] = [overlay.as_payload() for overlay in overlays]
    after = grid_identity(result)
    if after != before:
        raise AssertionError("overlay application mutated the Common Calendar surface")
    return result


def overlay_policy_payload() -> dict[str, Any]:
    return {
        "version": OVERLAY_POLICY_VERSION,
        "surface": {
            "authority": "calendar-law",
            "year_days": 364,
            "weeks_per_year": 52,
            "december_31_exists": False,
            "february_29_exists": False,
            "annual_weekday_pattern": "identical-every-year",
        },
        "canonical_overlays": sorted(CANONICAL_OVERLAY_KINDS),
        "witness_overlays": sorted(WITNESS_OVERLAY_KINDS),
        "overlay_jurisdiction": {
            "grid_authority": False,
            "rule": "inhabit-the-surface-never-rewrite-the-surface",
        },
    }
