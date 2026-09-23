from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Mapping

from .calendar import (
    CANONICAL_DAY001_WEEKDAY,
    CANONICAL_MONTH_LENGTHS,
    MONTH_LENGTHS,
    common_date,
    month_day_from_ordinal,
    ordinal_day,
    weekday_for_ordinal,
)

CANONICAL_YEAR_DAYS = 364
CANONICAL_WEEKS = 52
CANONICAL_FIRST_YEAR = 2026
CANONICAL_LAST_YEAR = 2075
CANONICAL_YEAR_COUNT = 50
CANONICAL_TOTAL_DAYS = CANONICAL_YEAR_DAYS * CANONICAL_YEAR_COUNT
ANCHOR_WEEKDAY = "Thursday"
FORBIDDEN_DATES = frozenset({(2, 29), (12, 31)})
CLOCK_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?$")


class RhythmAuthority(str, Enum):
    READ = "READ"
    COORDINATE = "COORDINATE"
    OBSERVE = "OBSERVE"
    OVERLAY = "OVERLAY"
    REJECT = "REJECT"


REQUESTABLE_AUTHORITIES = frozenset(
    {
        RhythmAuthority.READ,
        RhythmAuthority.COORDINATE,
        RhythmAuthority.OBSERVE,
        RhythmAuthority.OVERLAY,
    }
)


class CalendarInvariantViolation(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class CanonicalDate:
    year: int
    month: int
    day: int

    def __post_init__(self) -> None:
        ordinal_day(self.month, self.day)

    @property
    def ordinal(self) -> int:
        return ordinal_day(self.month, self.day)

    @property
    def weekday(self) -> str:
        return weekday_for_ordinal(self.ordinal)

    @property
    def label(self) -> str:
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"


@dataclass(frozen=True)
class RhythmRequest:
    authority: RhythmAuthority
    source: str
    canonical_date: CanonicalDate | None = None
    clock_time: str | None = None
    annotation: Mapping[str, Any] | None = None
    attempts_grid_mutation: bool = False
    dst_shift_seconds: int = 0
    intercalary_days: int = 0
    reconciliation_days: int = 0
    proposed_year_days: int | None = None
    proposed_weeks_per_year: int | None = None
    proposed_day001_weekday: str | None = None
    proposed_month_lengths: tuple[int, ...] | None = None


@dataclass(frozen=True)
class RhythmDecision:
    accepted: bool
    authority: RhythmAuthority
    source: str
    code: str
    reason: str
    canonical_date: CanonicalDate | None = None

    @property
    def surface_mutated(self) -> bool:
        return False


def assert_canonical_surface() -> None:
    """Fail closed if Calendar Core law drifts from the locked rhythm."""

    if MONTH_LENGTHS != CANONICAL_MONTH_LENGTHS:
        raise CalendarInvariantViolation(
            "MONTH_SEQUENCE_DRIFT",
            "canonical January 1 through December 30 sequence changed",
        )
    if sum(MONTH_LENGTHS) != CANONICAL_YEAR_DAYS:
        raise CalendarInvariantViolation(
            "YEAR_LENGTH_DRIFT",
            "canonical year must contain exactly 364 named dates",
        )
    if CANONICAL_YEAR_DAYS // 7 != CANONICAL_WEEKS:
        raise CalendarInvariantViolation(
            "WEEK_COUNT_DRIFT",
            "canonical year must contain exactly 52 complete weeks",
        )
    if CANONICAL_DAY001_WEEKDAY != ANCHOR_WEEKDAY:
        raise CalendarInvariantViolation(
            "ANCHOR_WEEKDAY_DRIFT",
            "January 1 must remain Thursday",
        )

    anchors = {
        (1, 1): "Thursday",
        (12, 10): "Thursday",
        (12, 30): "Wednesday",
    }
    for (month, day), expected in anchors.items():
        actual = weekday_for_ordinal(ordinal_day(month, day))
        if actual != expected:
            raise CalendarInvariantViolation(
                "ANCHOR_DATE_DRIFT",
                f"{month:02d}-{day:02d} must remain {expected}; got {actual}",
            )

    for month, day in FORBIDDEN_DATES:
        try:
            ordinal_day(month, day)
        except ValueError:
            continue
        raise CalendarInvariantViolation(
            "FORBIDDEN_DATE_BECAME_VALID",
            f"{month:02d}-{day:02d} must not exist in the canonical calendar",
        )


def validate_transition(previous: CanonicalDate, following: CanonicalDate) -> None:
    """Validate continuity without importing another calendar's rules."""

    if previous.ordinal == CANONICAL_YEAR_DAYS:
        expected = CanonicalDate(previous.year + 1, 1, 1)
    else:
        month, day = month_day_from_ordinal(previous.ordinal + 1)
        expected = CanonicalDate(previous.year, month, day)

    if following != expected:
        raise CalendarInvariantViolation(
            "INVALID_CANONICAL_TRANSITION",
            f"{previous.label} must transition directly to {expected.label}",
        )


class RhythmGovernor:
    """Authority boundary for the locked Common Calendar.

    Surface is immutable. Overlays are informative.

    The governor never computes a replacement calendar and exposes no ordinary
    mutation authority. Any request that would change the 364/52 rhythm is
    rejected and requires an explicit canonical reopening outside runtime.
    """

    def __init__(self) -> None:
        assert_canonical_surface()

    @staticmethod
    def _reject(
        request: RhythmRequest,
        code: str,
        reason: str,
    ) -> RhythmDecision:
        return RhythmDecision(
            accepted=False,
            authority=RhythmAuthority.REJECT,
            source=request.source,
            code=code,
            reason=reason,
            canonical_date=request.canonical_date,
        )

    def authorize(self, request: RhythmRequest) -> RhythmDecision:
        assert_canonical_surface()

        if not request.source.strip():
            return self._reject(
                request,
                "MISSING_SOURCE",
                "downstream requests must identify their source",
            )
        if request.authority not in REQUESTABLE_AUTHORITIES:
            return self._reject(
                request,
                "UNREQUESTABLE_AUTHORITY",
                "REJECT is an outcome; runtime has no MUTATE_CALENDAR authority",
            )
        if request.attempts_grid_mutation:
            return self._reject(
                request,
                "CANONICAL_REOPENING_REQUIRED",
                "runtime may not mutate the canonical surface",
            )
        if request.dst_shift_seconds != 0:
            return self._reject(
                request,
                "DST_FORBIDDEN",
                "DST adjustments are forbidden in the canonical clock coordinate",
            )
        if request.intercalary_days != 0:
            return self._reject(
                request,
                "INTERCALATION_FORBIDDEN",
                "intercalary days may not be inserted into the canonical grid",
            )
        if request.reconciliation_days != 0:
            return self._reject(
                request,
                "RECONCILIATION_FORBIDDEN",
                "reconciliation may not alter the canonical grid",
            )
        if (
            request.proposed_year_days is not None
            and request.proposed_year_days != CANONICAL_YEAR_DAYS
        ):
            return self._reject(
                request,
                "YEAR_LENGTH_MUTATION_FORBIDDEN",
                "canonical year length is exactly 364",
            )
        if (
            request.proposed_weeks_per_year is not None
            and request.proposed_weeks_per_year != CANONICAL_WEEKS
        ):
            return self._reject(
                request,
                "WEEK_COUNT_MUTATION_FORBIDDEN",
                "canonical year contains exactly 52 weeks",
            )
        if (
            request.proposed_day001_weekday is not None
            and request.proposed_day001_weekday != ANCHOR_WEEKDAY
        ):
            return self._reject(
                request,
                "ANCHOR_MUTATION_FORBIDDEN",
                "January 1 must remain Thursday",
            )
        if (
            request.proposed_month_lengths is not None
            and tuple(request.proposed_month_lengths) != CANONICAL_MONTH_LENGTHS
        ):
            return self._reject(
                request,
                "MONTH_SEQUENCE_MUTATION_FORBIDDEN",
                "January 1 through December 30 named-date sequence is immutable",
            )
        if request.clock_time is not None:
            if request.authority is not RhythmAuthority.COORDINATE:
                return self._reject(
                    request,
                    "CLOCK_AUTHORITY_MISMATCH",
                    "24-hour clock coordinates require COORDINATE authority",
                )
            if CLOCK_RE.fullmatch(request.clock_time) is None:
                return self._reject(
                    request,
                    "INVALID_24_HOUR_COORDINATE",
                    "clock time must be HH:MM or HH:MM:SS on the 24-hour clock",
                )

        return RhythmDecision(
            accepted=True,
            authority=request.authority,
            source=request.source,
            code="AUTHORIZED",
            reason="surface immutable; downstream operation remains within jurisdiction",
            canonical_date=request.canonical_date,
        )

    def require(self, request: RhythmRequest) -> RhythmDecision:
        decision = self.authorize(request)
        if not decision.accepted:
            raise CalendarInvariantViolation(decision.code, decision.reason)
        return decision


RHYTHM_GOVERNOR = RhythmGovernor()
