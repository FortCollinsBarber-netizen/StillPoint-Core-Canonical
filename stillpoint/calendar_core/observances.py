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
    note: str | None = None

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


# Canonical Firstfruits / Weeks placement for this Common Calendar:
# Unleavened Bread is M1D15..M1D21. The next weekly Sabbath is M1D24;
# Firstfruits is the following Sunday M1D25. Counting Firstfruits as day 1
# makes the fiftieth day M3D15. The source text is preserved separately from
# this ratified placement because the historical interpretation is contested.
SACRED_OBSERVANCES: tuple[Observance, ...] = (
    Observance(
        "passover",
        "Passover",
        "sacred",
        1,
        14,
        source_refs=(
            "Leviticus 23:5",
            "Numbers 28:16",
            "Deuteronomy 16:1-8",
        ),
    ),
    Observance(
        "unleavened-bread",
        "Feast of Unleavened Bread",
        "sacred",
        1,
        15,
        end_month=1,
        end_day=21,
        assembly=True,
        source_refs=(
            "Leviticus 23:6-8",
            "Numbers 28:17-25",
            "Deuteronomy 16:3-8",
        ),
    ),
    Observance(
        "firstfruits",
        "Firstfruits",
        "sacred",
        1,
        25,
        rule="canonical-sunday-after-weekly-sabbath-following-unleavened-bread",
        source_refs=("Leviticus 23:10-16",),
        note="Canonical Common Calendar placement; source interpretation remains provenance.",
    ),
    Observance(
        "weeks",
        "Feast of Weeks / Pentecost",
        "sacred",
        3,
        15,
        assembly=True,
        rule="canonical-fiftieth-day-counted-from-firstfruits",
        source_refs=(
            "Leviticus 23:15-21",
            "Numbers 28:26-31",
            "Deuteronomy 16:9-12",
            "Jubilees 6",
        ),
        note="Canonical Common Calendar placement downstream of Firstfruits.",
    ),
    Observance(
        "trumpets",
        "Trumpets",
        "sacred",
        7,
        1,
        assembly=True,
        source_refs=("Leviticus 23:23-25", "Numbers 29:1-6"),
    ),
    Observance(
        "atonement",
        "Day of Atonement",
        "sacred",
        7,
        10,
        assembly=True,
        source_refs=(
            "Leviticus 23:26-32",
            "Numbers 29:7-11",
            "Leviticus 25:9",
        ),
    ),
    Observance(
        "booths",
        "Feast of Booths",
        "sacred",
        7,
        15,
        end_month=7,
        end_day=21,
        assembly=True,
        source_refs=(
            "Leviticus 23:33-43",
            "Numbers 29:12-34",
            "Deuteronomy 16:13-17",
        ),
    ),
    Observance(
        "eighth-day",
        "Eighth Day Assembly",
        "sacred",
        7,
        22,
        assembly=True,
        source_refs=("Leviticus 23:36,39", "Numbers 29:35-38"),
    ),
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


# These civic/family recurrences are intentionally assigned fixed Common
# Calendar addresses. They are not claims that the external Gregorian legal
# calendar has changed; they are StillPoint Common Calendar observances.
CIVIC_OBSERVANCES: tuple[Observance, ...] = (
    Observance("new-year", "New Year's Day", "civic", 1, 1),
    Observance("valentines-day", "Valentine's Day", "civic-family", 2, 14),
    Observance(
        "mlk-day",
        "Martin Luther King Jr. Day",
        "civic",
        1,
        19,
        rule="third-monday-january-on-fixed-common-grid",
    ),
    Observance(
        "washington-birthday",
        "Washington's Birthday",
        "civic",
        2,
        16,
        rule="third-monday-february-on-fixed-common-grid",
    ),
    Observance(
        "good-friday",
        "Good Friday",
        "christian-civic",
        4,
        3,
        rule="2026-seed-position-on-fixed-common-grid",
    ),
    Observance(
        "easter-sunday",
        "Easter Sunday",
        "christian-civic",
        4,
        5,
        rule="2026-seed-position-on-fixed-common-grid",
    ),
    Observance(
        "mothers-day",
        "Mother's Day",
        "civic-family",
        5,
        10,
        rule="second-sunday-may-on-fixed-common-grid",
    ),
    Observance(
        "memorial-day",
        "Memorial Day",
        "civic",
        5,
        25,
        rule="last-monday-may-on-fixed-common-grid",
    ),
    Observance("juneteenth", "Juneteenth National Independence Day", "civic", 6, 19),
    Observance(
        "fathers-day",
        "Father's Day",
        "civic-family",
        6,
        21,
        rule="third-sunday-june-on-fixed-common-grid",
    ),
    Observance("independence-day", "Independence Day", "civic", 7, 4),
    Observance(
        "labor-day",
        "Labor Day",
        "civic",
        9,
        7,
        rule="first-monday-september-on-fixed-common-grid",
    ),
    Observance(
        "columbus-day",
        "Columbus Day",
        "civic",
        10,
        12,
        rule="second-monday-october-on-fixed-common-grid",
    ),
    Observance("halloween", "Halloween", "civic-family", 10, 31),
    Observance("veterans-day", "Veterans Day", "civic", 11, 11),
    Observance(
        "thanksgiving",
        "Thanksgiving Day",
        "civic",
        11,
        26,
        rule="fourth-thursday-november-on-fixed-common-grid",
    ),
    Observance("christmas-eve", "Christmas Eve", "christian-civic", 12, 24),
    Observance("christmas", "Christmas Day", "civic", 12, 25),
    Observance(
        "new-years-eve",
        "New Year's Eve",
        "civic",
        12,
        30,
        rule="final-day-of-common-year",
        note="December 31 does not exist in the Common Calendar.",
    ),
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
        item
        for item in ALL_OBSERVANCES
        if item.contains_ordinal(ordinal)
        and (allowed is None or item.jurisdiction in allowed)
    )
