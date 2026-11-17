"""An explicitly proposed StillPoint overlay, distinct from civil month names.

March 25 is a modern project anchor, not an ancient Common Calendar date or a
rule for other communities. The anchor is fixed, with no annual solar reset.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .calendar import common_date, ordinal_day

SACRED_MONTH_LENGTHS = (30, 30, 31) * 4
PROFILE_ID = "stillpoint-enochic-march25-v1"
PROFILE_STATUS = "proposed-project-rule-awaiting-author-selection"
JUBILEE_EPOCH_COMMON_YEAR = 2027
JUBILEE_ROLLOVER_RULE = "overlap-49"


@dataclass(frozen=True)
class SacredYearProfile:
    id: str = PROFILE_ID
    anchor_common_month: int = 3
    anchor_common_day: int = 25

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id:
            raise ValueError("sacred profile needs a nonempty identifier")
        if type(self.anchor_common_month) is not int or type(self.anchor_common_day) is not int:
            raise ValueError("sacred anchor coordinates must be integers")
        anchor = ordinal_day(self.anchor_common_month, self.anchor_common_day)
        if common_date(year=2026, ordinal=anchor).weekday != "Wednesday":
            raise ValueError("this Wednesday-start sacred profile requires a Wednesday anchor")

    @property
    def anchor_ordinal(self) -> int:
        return ordinal_day(self.anchor_common_month, self.anchor_common_day)


DEFAULT_SACRED_PROFILE = SacredYearProfile()


def sacred_ordinal(month: int, day: int) -> int:
    if type(month) is not int or type(day) is not int:
        raise ValueError("sacred month and day must be integers")
    if not 1 <= month <= 12 or not 1 <= day <= SACRED_MONTH_LENGTHS[month - 1]:
        raise ValueError("invalid 30/30/31 sacred address")
    return sum(SACRED_MONTH_LENGTHS[:month - 1]) + day


def sacred_month_day(ordinal: int) -> tuple[int, int]:
    if type(ordinal) is not int or not 1 <= ordinal <= 364:
        raise ValueError("sacred ordinal must be within 1..364")
    remaining = ordinal
    for month, length in enumerate(SACRED_MONTH_LENGTHS, 1):
        if remaining <= length:
            return month, remaining
        remaining -= length
    raise AssertionError("unreachable")


def common_from_sacred(
    sacred_year: int, month: int, day: int,
    *, profile: SacredYearProfile = DEFAULT_SACRED_PROFILE,
):
    if type(sacred_year) is not int:
        raise ValueError("sacred year label must be an integer")
    offset = profile.anchor_ordinal - 1 + sacred_ordinal(month, day) - 1
    year_offset, day_index = divmod(offset, 364)
    return common_date(year=sacred_year + year_offset, ordinal=day_index + 1)


def sacred_from_common(
    common_year: int, month: int, day: int,
    *, profile: SacredYearProfile = DEFAULT_SACRED_PROFILE,
) -> dict[str, Any]:
    if type(common_year) is not int:
        raise ValueError("Common year label must be an integer")
    if type(month) is not int or type(day) is not int:
        raise ValueError("Common month and day must be integers")
    offset = ordinal_day(month, day) - profile.anchor_ordinal
    year_offset, day_index = divmod(offset, 364)
    source_month, source_day = sacred_month_day(day_index + 1)
    return {
        "profile_id": profile.id, "calendar": "schematic-enochic-364",
        "year": common_year + year_offset, "month": source_month,
        "day": source_day, "ordinal": day_index + 1,
    }


def sacred_profile_payload() -> dict[str, Any]:
    return {
        "id": PROFILE_ID,
        "selectionStatus": PROFILE_STATUS,
        "authorityScope": "StillPoint-religious-overlay-only",
        "sourceCalendar": "schematic-enochic-364",
        "monthLengths": list(SACRED_MONTH_LENGTHS),
        "anchorCommonMonth": 3, "anchorCommonDay": 25,
        "anchorWeekday": "Wednesday",
        "firstfruitsSourceMonth": 1, "firstfruitsSourceDay": 26,
        "firstfruitsRule": "sunday-after-weekly-sabbath-following-unleavened-bread",
        "weeksSourceMonth": 3, "weeksSourceDay": 15,
        "annualSolarReset": False, "gridAuthority": False,
        "note": "Fixed modern project convention; not an ancient Common date or a rule for other communities.",
    }


def long_cycle_policy_payload() -> dict[str, Any]:
    return {
        "id": "stillpoint-overlap49-2027-v1",
        "selectionStatus": PROFILE_STATUS,
        "authorityScope": "project-calculation-and-proposed-policy-only",
        "epochCommonYear": JUBILEE_EPOCH_COMMON_YEAR, "epochCycle": 1,
        "rolloverRule": JUBILEE_ROLLOVER_RULE, "cycleYears": 49,
        "proclamationOrdinalYear": 50,
        "year50OverlapsNextYear1": True,
        "releaseObservanceId": "atonement", "gridAuthority": False,
    }
