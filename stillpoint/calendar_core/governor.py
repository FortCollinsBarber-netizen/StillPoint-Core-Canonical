"""Rhythm Governor: authority boundary for the locked Common Calendar.

This module is deliberately not a calendar engine. Calendar Core owns the
canonical 364-day / 52-week surface. RhythmGovernor protects that surface from
downstream mutation while allowing bounded reads, coordination, observations,
and overlays.

Governing distinction:

    Surface is immutable. Overlays are informative.

There is intentionally no ordinary MUTATE_CALENDAR authority. Any proposal to
change the canonical geometry requires an explicit human canonical reopening
outside this runtime API.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .calendar import (
    CANONICAL_DAY001_WEEKDAY,
    CANONICAL_TEMPLATE_YEAR,
    MONTH_LENGTHS,
    MONTH_NAMES,
    common_date,
    month_day_from_ordinal,
    ordinal_day,
    validate_grid,
)
from .runtime_surface import calendar_day_payload, load_enacted_publication
from .spec import build_calendar_core_spec


GOVERNOR_SCHEMA = "stillpoint.rhythm-governor.v1"
GOVERNING_RULE = "surface-immutable-overlays-informative"

_CANONICAL_MONTH_NAMES = (
    "January", "February", "March", "April",
    "May", "June", "July", "August",
    "September", "October", "November", "December",
)
_CANONICAL_MONTH_LENGTHS = (
    31, 28, 31, 30, 31, 30,
    31, 31, 30, 31, 30, 30,
)
_CANONICAL_FIRST_YEAR = 2026
_CANONICAL_LAST_YEAR = 2075
_CANONICAL_YEAR_COUNT = 50
_CANONICAL_YEAR_DAYS = 364
_CANONICAL_WEEKS = 52

# These are request-envelope keys that explicitly attempt to acquire grid
# mutation jurisdiction. Ordinary observations may describe anything; they
# simply cannot submit it as a surface patch.
_MUTATION_ENVELOPE_KEYS = frozenset(
    {
        "surface_patch",
        "calendar_patch",
        "grid_patch",
        "canonical_patch",
        "proposed_surface_change",
        "mutate_calendar",
        "mutate_grid",
        "insert_day",
        "remove_date",
        "intercalate",
        "reconcile_calendar",
        "reanchor_weekday",
    }
)

# Coordination may carry local/civil timezone context, but the Common Clock
# itself may not acquire a DST jump.
_DST_ENABLE_KEYS = frozenset(
    {
        "apply_dst",
        "dst_enabled",
        "use_dst",
        "daylight_saving_enabled",
        "common_standard_uses_dst",
    }
)
_DST_SHIFT_KEYS = frozenset(
    {
        "dst_shift_seconds",
        "daylight_saving_shift_seconds",
        "clock_jump_seconds",
    }
)


class CalendarAuthority(str, Enum):
    READ = "READ"
    COORDINATE = "COORDINATE"
    OBSERVE = "OBSERVE"
    OVERLAY = "OVERLAY"
    REJECT = "REJECT"


INHABITANT_LAYER_POLICY = {
    "feasts": CalendarAuthority.OVERLAY,
    "sabbath": CalendarAuthority.OVERLAY,
    "stillpoint": CalendarAuthority.OVERLAY,
    "seasons": CalendarAuthority.OVERLAY,
    "lunar-witness": CalendarAuthority.OBSERVE,
    "jewish-overlay": CalendarAuthority.OVERLAY,
    "islamic-overlay": CalendarAuthority.OVERLAY,
    "seven-year-cycle": CalendarAuthority.OVERLAY,
    "forty-nine-year-cycle": CalendarAuthority.OVERLAY,
    "jubilee": CalendarAuthority.OVERLAY,
    "local-light": CalendarAuthority.OBSERVE,
}


class CalendarInvariantViolation(ValueError):
    """Raised when the canonical calendar surface no longer matches its lock."""


class CalendarAuthorityViolation(PermissionError):
    """Raised when a request asks for authority the Governor does not grant."""


@dataclass(frozen=True)
class CanonicalDate:
    year: int
    month: int
    day: int
    ordinal: int
    week: int
    day_in_week: int
    weekday: str

    @property
    def address(self) -> str:
        return f"Y_{self.year}-{self.ordinal:03d}"


@dataclass(frozen=True)
class GovernorDecision:
    requested_action: str
    authority: CalendarAuthority
    allowed: bool
    reason: str
    surface_digest: str
    canonical_reopening_required: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": GOVERNOR_SCHEMA,
            "governing_rule": GOVERNING_RULE,
            "requested_action": self.requested_action,
            "authority": self.authority.value,
            "allowed": self.allowed,
            "reason": self.reason,
            "surface_digest": self.surface_digest,
            "canonical_reopening_required": self.canonical_reopening_required,
        }


def _canonical_surface_document() -> dict[str, Any]:
    return {
        "template_year": CANONICAL_TEMPLATE_YEAR,
        "first_year": _CANONICAL_FIRST_YEAR,
        "last_year": _CANONICAL_LAST_YEAR,
        "year_count": _CANONICAL_YEAR_COUNT,
        "year_days": _CANONICAL_YEAR_DAYS,
        "weeks_per_year": _CANONICAL_WEEKS,
        "day001_weekday": CANONICAL_DAY001_WEEKDAY,
        "month_names": list(MONTH_NAMES),
        "month_lengths": list(MONTH_LENGTHS),
        "year_opening": {"month": 1, "day": 1},
        "year_closing": {"month": 12, "day": 30},
        "has_february_29": False,
        "has_december_31": False,
        "annual_transition": "DECEMBER_30_TO_JANUARY_1",
        "dst": "forbidden-on-common-clock",
        "coordination_clock": "24-hour",
        "observation_authority": "annotate-only-no-grid-mutation",
        "inhabitant_layers": {
            layer: authority.value
            for layer, authority in INHABITANT_LAYER_POLICY.items()
        },
        "inhabitant_surface_authority": "none",
    }


def canonical_surface_digest() -> str:
    encoded = json.dumps(
        _canonical_surface_document(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _walk_mapping(value: Any):
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield str(key), child
            yield from _walk_mapping(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _walk_mapping(child)


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "false", "no", "off", "none"}
    return bool(value)


class RhythmGovernor:
    """Protect the immutable Common Calendar surface.

    The Governor can authorize bounded operations but exposes no surface
    mutation method. Downstream systems may read, coordinate, observe, or
    overlay. Any explicit attempt to patch the canonical grid is rejected.
    """

    def __init__(
        self,
        *,
        publication_path: Path | str | None = None,
    ) -> None:
        self.publication_path = publication_path

    @property
    def surface_digest(self) -> str:
        return canonical_surface_digest()

    def assert_surface_integrity(self) -> dict[str, Any]:
        validate_grid()

        if tuple(MONTH_NAMES) != _CANONICAL_MONTH_NAMES:
            raise CalendarInvariantViolation(
                "month identities drifted; January through December are locked"
            )
        if tuple(MONTH_LENGTHS) != _CANONICAL_MONTH_LENGTHS:
            raise CalendarInvariantViolation(
                "named-date sequence drifted; only December 31 may be removed"
            )
        if CANONICAL_TEMPLATE_YEAR != 2026:
            raise CalendarInvariantViolation("canonical template year must remain 2026")
        if CANONICAL_DAY001_WEEKDAY != "Thursday":
            raise CalendarInvariantViolation("January 1 must remain Thursday")
        if sum(MONTH_LENGTHS) != _CANONICAL_YEAR_DAYS:
            raise CalendarInvariantViolation("canonical year must contain 364 dates")
        if _CANONICAL_YEAR_DAYS // 7 != _CANONICAL_WEEKS:
            raise CalendarInvariantViolation("canonical year must contain 52 weeks")

        if ordinal_day(12, 10) != 344:
            raise CalendarInvariantViolation("December 10 must remain ordinal 344")
        if common_date(year=2026, ordinal=ordinal_day(12, 10)).weekday != "Thursday":
            raise CalendarInvariantViolation("December 10 must remain Thursday")
        if common_date(year=2026, ordinal=ordinal_day(12, 30)).weekday != "Wednesday":
            raise CalendarInvariantViolation("December 30 must remain Wednesday")

        for month, day in ((2, 29), (12, 31)):
            try:
                ordinal_day(month, day)
            except ValueError:
                pass
            else:
                raise CalendarInvariantViolation(
                    f"{month}/{day} must not exist in the canonical calendar"
                )

        spec = build_calendar_core_spec()
        ordinary = spec["ordinaryCalendar"]
        transition = spec["annualTransition"]
        if ordinary["baseYearDays"] != 364 or ordinary["weeksPerYear"] != 52:
            raise CalendarInvariantViolation("Calendar Core geometry drifted")
        if ordinary["day001Weekday"] != "Thursday":
            raise CalendarInvariantViolation("Calendar Core weekday anchor drifted")
        if ordinary["hasFebruary29"] or ordinary["hasDecember31"]:
            raise CalendarInvariantViolation("forbidden extra date became valid")
        if transition["interannualDays"] != 0 or transition["reconciliationAllowed"]:
            raise CalendarInvariantViolation(
                "intercalation/reconciliation acquired calendar authority"
            )

        document = load_enacted_publication(self.publication_path)
        rows = document["years"]
        if len(rows) != _CANONICAL_YEAR_COUNT:
            raise CalendarInvariantViolation("enacted publication must contain 50 years")
        if int(rows[0]["year"]) != _CANONICAL_FIRST_YEAR:
            raise CalendarInvariantViolation("publication must begin at 2026")
        if int(rows[-1]["year"]) != _CANONICAL_LAST_YEAR:
            raise CalendarInvariantViolation("publication must end at 2075")

        openings = [date.fromisoformat(str(row["openingCivilDate"])) for row in rows]
        for left, right in zip(openings, openings[1:]):
            if (right - left).days != _CANONICAL_YEAR_DAYS:
                raise CalendarInvariantViolation(
                    "publication year opening moved by something other than 364 days"
                )

        return {
            "schema": GOVERNOR_SCHEMA,
            "governing_rule": GOVERNING_RULE,
            "surface_digest": self.surface_digest,
            "template_year": CANONICAL_TEMPLATE_YEAR,
            "year_days": _CANONICAL_YEAR_DAYS,
            "weeks_per_year": _CANONICAL_WEEKS,
            "year_count": len(rows),
            "total_dates": len(rows) * _CANONICAL_YEAR_DAYS,
            "first_year": int(rows[0]["year"]),
            "last_year": int(rows[-1]["year"]),
            "day001_weekday": CANONICAL_DAY001_WEEKDAY,
            "december_31_exists": False,
            "february_29_exists": False,
            "ordinary_mutation_authority_exists": False,
            "inhabitant_layers": {
                layer: authority.value
                for layer, authority in INHABITANT_LAYER_POLICY.items()
            },
            "inhabitant_surface_authority": "none",
        }

    def validate_date(self, year: int, month: int, day: int) -> CanonicalDate:
        self.assert_surface_integrity()
        ordinal = ordinal_day(int(month), int(day))
        value = common_date(year=int(year), ordinal=ordinal)
        return CanonicalDate(
            year=value.year,
            month=value.month,
            day=value.day,
            ordinal=value.ordinal,
            week=value.week,
            day_in_week=value.day_in_week,
            weekday=value.weekday,
        )

    def next_date(self, year: int, month: int, day: int) -> CanonicalDate:
        current = self.validate_date(year, month, day)
        if current.month == 12 and current.day == 30:
            return self.validate_date(current.year + 1, 1, 1)
        next_month, next_day = month_day_from_ordinal(current.ordinal + 1)
        return self.validate_date(current.year, next_month, next_day)

    def weekday_for(self, year: int, month: int, day: int) -> str:
        return self.validate_date(year, month, day).weekday

    def decide(
        self,
        action: CalendarAuthority | str,
        *,
        payload: Mapping[str, Any] | None = None,
        proposed_surface_change: Mapping[str, Any] | None = None,
    ) -> GovernorDecision:
        self.assert_surface_integrity()
        requested = action.value if isinstance(action, CalendarAuthority) else str(action)
        try:
            authority = (
                action
                if isinstance(action, CalendarAuthority)
                else CalendarAuthority(requested.upper())
            )
        except ValueError:
            return self._reject(
                requested,
                "unknown calendar authority; ordinary mutation authority does not exist",
                reopening=True,
            )

        if authority is CalendarAuthority.REJECT:
            return self._reject(requested, "request explicitly rejected")

        if proposed_surface_change:
            return self._reject(
                requested,
                "canonical surface changes require explicit human reopening",
                reopening=True,
            )

        body = dict(payload or {})
        for key, value in _walk_mapping(body):
            normalized = key.strip().lower()
            if normalized in _MUTATION_ENVELOPE_KEYS:
                return self._reject(
                    requested,
                    f"request contains forbidden calendar mutation envelope: {key}",
                    reopening=True,
                )
            if authority is CalendarAuthority.COORDINATE:
                if normalized in _DST_ENABLE_KEYS and _truthy(value):
                    return self._reject(
                        requested,
                        "DST adjustment is forbidden on the Common Clock",
                        reopening=True,
                    )
                if normalized in _DST_SHIFT_KEYS and _truthy(value):
                    return self._reject(
                        requested,
                        "clock jump/DST shift is forbidden on the Common Clock",
                        reopening=True,
                    )

        return GovernorDecision(
            requested_action=requested,
            authority=authority,
            allowed=True,
            reason={
                CalendarAuthority.READ: "read may inspect but not mutate the canonical surface",
                CalendarAuthority.COORDINATE: "24-hour coordination is allowed without DST mutation",
                CalendarAuthority.OBSERVE: "observation may record events without grid authority",
                CalendarAuthority.OVERLAY: "overlay may annotate a canonical address without grid authority",
            }[authority],
            surface_digest=self.surface_digest,
            canonical_reopening_required=False,
        )

    def require(
        self,
        action: CalendarAuthority | str,
        *,
        payload: Mapping[str, Any] | None = None,
        proposed_surface_change: Mapping[str, Any] | None = None,
    ) -> GovernorDecision:
        decision = self.decide(
            action,
            payload=payload,
            proposed_surface_change=proposed_surface_change,
        )
        if not decision.allowed:
            raise CalendarAuthorityViolation(decision.reason)
        return decision

    def read_day(self, year: int, ordinal: int) -> dict[str, Any]:
        self.require(CalendarAuthority.READ)
        return calendar_day_payload(
            int(year),
            int(ordinal),
            publication_path=self.publication_path,
        )

    def annotate(
        self,
        action: CalendarAuthority | str,
        *,
        year: int,
        month: int,
        day: int,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        decision = self.require(action, payload=payload)
        if decision.authority not in {
            CalendarAuthority.OBSERVE,
            CalendarAuthority.OVERLAY,
        }:
            raise CalendarAuthorityViolation(
                "annotations require OBSERVE or OVERLAY authority"
            )
        target = self.validate_date(year, month, day)
        return {
            "schema": GOVERNOR_SCHEMA,
            "governing_rule": GOVERNING_RULE,
            "authority": decision.authority.value,
            "calendar_address": target.address,
            "canonical_date": {
                "year": target.year,
                "month": target.month,
                "day": target.day,
                "ordinal": target.ordinal,
                "weekday": target.weekday,
            },
            "annotation": dict(payload),
            "surface_digest": decision.surface_digest,
            "grid_mutated": False,
        }

    def inhabit(
        self,
        layer: str,
        *,
        year: int,
        month: int,
        day: int,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Attach a recognized layer to the surface without granting grid authority."""

        layer_id = str(layer).strip().lower()
        authority = INHABITANT_LAYER_POLICY.get(layer_id)
        if authority is None:
            raise CalendarAuthorityViolation(
                f"unknown inhabitant layer: {layer}; no authority inferred"
            )
        envelope = self.annotate(
            authority,
            year=year,
            month=month,
            day=day,
            payload={
                "layer": layer_id,
                "layer_payload": dict(payload),
                "surface_authority": "none",
            },
        )
        return {
            **envelope,
            "layer": layer_id,
            "layer_authority": authority.value,
            "surface_authority": "none",
        }

    def _reject(
        self,
        requested: str,
        reason: str,
        *,
        reopening: bool = False,
    ) -> GovernorDecision:
        return GovernorDecision(
            requested_action=requested,
            authority=CalendarAuthority.REJECT,
            allowed=False,
            reason=reason,
            surface_digest=self.surface_digest,
            canonical_reopening_required=reopening,
        )
