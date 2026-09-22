from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .calendar import ordinal_day


@dataclass(frozen=True)
class Observance:
    id: str
    name: str
    jurisdiction: str
    month: int
    day: int
    end_month: int | None = None
    end_day: int | None = None
    assembly: bool = False
    rule: str = "fixed-date"
    source_refs: tuple[str, ...] = ()

    @property
    def start_ordinal(self) -> int:
        return ordinal_day(self.month, self.day)

    @property
    def end_ordinal(self) -> int:
        if self.end_month is None or self.end_day is None:
            return self.start_ordinal
        return ordinal_day(self.end_month, self.end_day)

    def contains_ordinal(self, ordinal: int) -> bool:
        return self.start_ordinal <= ordinal <= self.end_ordinal


# Firstfruits / Weeks lock:
# - Unleavened Bread is M1D15..M1D21.
# - The first weekly Sabbath after that completed feast is M1D24.
# - Firstfruits is the following Sunday, M1D25.
# - Counting Firstfruits as day 1 makes the fiftieth day M3D15.
# This is the ratified Common Calendar interpretation used by the map. It is
# recorded as a derivation rather than presented as the only historical
# interpretation of Leviticus 23.
SACRED_OBSERVANCES: tuple[Observance, ...] = (
    Observance(
        id="passover",
        name="Passover",
        jurisdiction="sacred",
        month=1,
        day=14,
        source_refs=("Leviticus 23:5", "Numbers 28:16", "Deuteronomy 16:1-8"),
    ),
    Observance(
        id="unleavened-bread",
        name="Feast of Unleavened Bread",
        jurisdiction="sacred",
        month=1,
        day=15,
        end_month=1,
        end_day=21,
        assembly=True,
        source_refs=("Leviticus 23:6-8", "Numbers 28:17-25", "Deuteronomy 16:3-8"),
    ),
    Observance(
        id="firstfruits",
        name="Firstfruits",
        jurisdiction="sacred",
        month=1,
        day=25,
        rule="first-sunday-after-the-weekly-sabbath-following-unleavened-bread",
        source_refs=("Leviticus 23:10-16",),
    ),
    Observance(
        id="weeks",
        name="Feast of Weeks / Pentecost",
        jurisdiction="sacred",
        month=3,
        day=15,
        assembly=True,
        rule="fiftieth-day-counted-from-firstfruits",
        source_refs=(
            "Leviticus 23:15-21",
            "Numbers 28:26-31",
            "Deuteronomy 16:9-12",
            "Jubilees 6; 15; 44",
        ),
    ),
    Observance(
        id="trumpets",
        name="Trumpets",
        jurisdiction="sacred",
        month=7,
        day=1,
        assembly=True,
        source_refs=("Leviticus 23:23-25", "Numbers 29:1-6"),
    ),
    Observance(
        id="atonement",
        name="Day of Atonement",
        jurisdiction="sacred",
        month=7,
        day=10,
        assembly=True,
        source_refs=("Leviticus 23:26-32", "Numbers 29:7-11", "Leviticus 25:9"),
    ),
    Observance(
        id="booths",
        name="Feast of Booths",
        jurisdiction="sacred",
        month=7,
        day=15,
        end_month=7,
        end_day=21,
        assembly=True,
        source_refs=("Leviticus 23:33-43", "Numbers 29:12-34", "Deuteronomy 16:13-17"),
    ),
    Observance(
        id="eighth-day",
        name="Eighth Day Assembly",
        jurisdiction="sacred",
        month=7,
        day=22,
        assembly=True,
        source_refs=("Leviticus 23:36,39", "Numbers 29:35-38"),
    ),
)


CIVIC_OBSERVANCES: tuple[Observance, ...] = (
    Observance("new-year", "New Year's Day", "civic", 1, 1, source_refs=("StillPoint fixed civic recurrence",)),
    Observance("mlk-day", "Martin Luther King Jr. Day", "civic", 1, 19, rule="third-monday-january", source_refs=("U.S. civic recurrence",)),
    Observance("washington-birthday", "Washington's Birthday", "civic", 2, 16, rule="third-monday-february", source_refs=("U.S. civic recurrence",)),
    Observance("mothers-day", "Mother's Day", "civic-family", 5, 10, rule="second-sunday-may", source_refs=("U.S. civic recurrence",)),
    Observance("memorial-day", "Memorial Day", "civic", 5, 25, rule="last-monday-may", source_refs=("U.S. civic recurrence",)),
    Observance("juneteenth", "Juneteenth National Independence Day", "civic", 6, 19, source_refs=("U.S. civic recurrence",)),
    Observance("fathers-day", "Father's Day", "civic-family", 6, 21, rule="third-sunday-june", source_refs=("U.S. civic recurrence",)),
    Observance("independence-day", "Independence Day", "civic", 7, 4, source_refs=("U.S. civic recurrence",)),
    Observance("labor-day", "Labor Day", "civic", 9, 7, rule="first-monday-september", source_refs=("U.S. civic recurrence",)),
    Observance("columbus-day", "Columbus Day", "civic", 10, 12, rule="second-monday-october", source_refs=("U.S. civic recurrence",)),
    Observance("veterans-day", "Veterans Day", "civic", 11, 11, source_refs=("U.S. civic recurrence",)),
    Observance("thanksgiving", "Thanksgiving Day", "civic", 11, 26, rule="fourth-thursday-november", source_refs=("U.S. civic recurrence",)),
    Observance("christmas", "Christmas Day", "civic", 12, 25, source_refs=("StillPoint fixed civic recurrence",)),
)


MONTH_OPENINGS: tuple[Observance, ...] = tuple(
    Observance(
        id=f"month-{month:02d}-opening",
        name=f"Month {month} Opening",
        jurisdiction="sacred-marker",
        month=month,
        day=1,
        source_refs=("Numbers 28:11-15",),
    )
    for month in range(1, 13)
)


ALL_OBSERVANCES: tuple[Observance, ...] = (
    MONTH_OPENINGS + SACRED_OBSERVANCES + CIVIC_OBSERVANCES
)


def observances_for_ordinal(
    ordinal: int,
    *,
    include_jurisdictions: Iterable[str] | None = None,
) -> tuple[Observance, ...]:
    allowed = (
        None
        if include_jurisdictions is None
        else set(include_jurisdictions)
    )
    return tuple(
        observance
        for observance in ALL_OBSERVANCES
        if observance.contains_ordinal(ordinal)
        and (
            allowed is None
            or observance.jurisdiction in allowed
        )
    )
