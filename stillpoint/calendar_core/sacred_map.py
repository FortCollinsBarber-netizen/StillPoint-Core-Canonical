from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .calendar import (
    DAY001_WEEKDAY,
    MONTH_LENGTHS,
    WEEKDAYS,
    common_date,
    month_day_from_ordinal,
    ordinal_day,
    weekday_for_ordinal,
)
from .gates import GATE_SEQUENCE, PHASE_LENGTHS, phase_for_base_day
from .jubilee import jubilee_state

MAP_VERSION = "stillpoint-sacred-civic-map-v1"
DEFAULT_CYCLE_YEARS = 50

ENOCHIC_SOURCES = ("1 Enoch 72-82", "Jubilees 6:32-38")


@dataclass(frozen=True)
class Observance:
    id: str
    name: str
    category: str
    rule: str
    ordinal: int
    month: int
    day: int
    weekday: str
    sources: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "rule": self.rule,
            "ordinal": self.ordinal,
            "month": self.month,
            "day": self.day,
            "weekday": self.weekday,
            "sources": list(self.sources),
        }


def _fixed(
    id: str,
    name: str,
    category: str,
    month: int,
    day: int,
    sources: tuple[str, ...],
    *,
    rule: str = "fixed_date",
) -> Observance:
    ordinal = ordinal_day(month, day)
    return Observance(
        id=id,
        name=name,
        category=category,
        rule=rule,
        ordinal=ordinal,
        month=month,
        day=day,
        weekday=weekday_for_ordinal(ordinal),
        sources=sources,
    )


def _nth_weekday(month: int, weekday: str, occurrence: int) -> int:
    if weekday not in WEEKDAYS:
        raise ValueError(f"unknown weekday: {weekday}")
    dates = [
        day
        for day in range(1, MONTH_LENGTHS[month - 1] + 1)
        if weekday_for_ordinal(ordinal_day(month, day)) == weekday
    ]
    if not dates or occurrence == 0:
        raise ValueError("invalid weekday recurrence")
    try:
        return dates[occurrence - 1] if occurrence > 0 else dates[occurrence]
    except IndexError as exc:
        raise ValueError("weekday recurrence does not exist in fixed month") from exc


def resolved_observances() -> tuple[Observance, ...]:
    items: list[Observance] = [
        _fixed(
            "new-year",
            "New Year",
            "civic",
            1,
            1,
            ("StillPoint fixed-grid enactment",),
        ),
        _fixed(
            "passover",
            "Passover",
            "appointed-time",
            1,
            14,
            ("Leviticus 23:5", "Numbers 28:16", "Deuteronomy 16:1-8"),
        ),
        _fixed(
            "unleavened-bread-open",
            "Unleavened Bread — opening assembly",
            "appointed-time",
            1,
            15,
            ("Leviticus 23:6-8", "Numbers 28:17-25"),
        ),
        _fixed(
            "unleavened-bread-close",
            "Unleavened Bread — closing assembly",
            "appointed-time",
            1,
            21,
            ("Leviticus 23:6-8", "Numbers 28:17-25"),
        ),
        _fixed(
            "trumpets",
            "Trumpets / Memorial of Blowing",
            "appointed-time",
            7,
            1,
            ("Leviticus 23:23-25", "Numbers 29:1-6"),
        ),
        _fixed(
            "atonement",
            "Day of Atonement",
            "appointed-time",
            7,
            10,
            (
                "Leviticus 16",
                "Leviticus 23:26-32",
                "Numbers 29:7-11",
                "Leviticus 25:9",
            ),
        ),
        _fixed(
            "booths-open",
            "Booths / Tabernacles — opening assembly",
            "appointed-time",
            7,
            15,
            (
                "Leviticus 23:33-43",
                "Numbers 29:12-38",
                "Deuteronomy 16:13-15",
            ),
        ),
        _fixed(
            "booths-seventh",
            "Booths / Tabernacles — seventh day",
            "appointed-time",
            7,
            21,
            ("Leviticus 23:33-43", "Numbers 29:12-38"),
        ),
        _fixed(
            "eighth-day",
            "Eighth Day assembly",
            "appointed-time",
            7,
            22,
            ("Leviticus 23:36,39", "Numbers 29:35-38"),
        ),
        _fixed(
            "juneteenth",
            "Juneteenth",
            "civic",
            6,
            19,
            ("StillPoint fixed civic recurrence registry",),
        ),
        _fixed(
            "independence-day",
            "Independence Day",
            "civic",
            7,
            4,
            ("StillPoint fixed civic recurrence registry",),
        ),
        _fixed(
            "veterans-day",
            "Veterans Day",
            "civic",
            11,
            11,
            ("StillPoint fixed civic recurrence registry",),
        ),
        _fixed(
            "december-10-anchor",
            "December 10 Anchor",
            "civic",
            12,
            10,
            ("StillPoint fixed-grid enactment",),
        ),
        _fixed(
            "christmas",
            "Christmas",
            "civic-religious",
            12,
            25,
            ("StillPoint fixed civic/religious recurrence registry",),
        ),
    ]

    sabbath_in_unleavened = next(
        day
        for day in range(15, 22)
        if weekday_for_ordinal(ordinal_day(1, day)) == "Saturday"
    )
    firstfruits_ordinal = ordinal_day(1, sabbath_in_unleavened) + 1
    firstfruits_month, firstfruits_day = month_day_from_ordinal(firstfruits_ordinal)
    items.append(
        _fixed(
            "firstfruits",
            "Firstfruits",
            "appointed-time",
            firstfruits_month,
            firstfruits_day,
            ("Leviticus 23:9-14",),
            rule="day_after_weekly_sabbath_within_unleavened_bread",
        )
    )

    weeks_ordinal = firstfruits_ordinal + 49
    weeks_month, weeks_day = month_day_from_ordinal(weeks_ordinal)
    items.append(
        _fixed(
            "weeks",
            "Weeks / Pentecost",
            "appointed-time",
            weeks_month,
            weeks_day,
            ("Leviticus 23:15-21", "Numbers 28:26-31", "Deuteronomy 16:9-12"),
            rule="fifty_day_count_from_firstfruits",
        )
    )

    weekday_rules = (
        ("mlk-day", "Martin Luther King Jr. Day", 1, "Monday", 3),
        ("washington-birthday", "Washington's Birthday / Presidents Day", 2, "Monday", 3),
        ("mothers-day", "Mother's Day", 5, "Sunday", 2),
        ("memorial-day", "Memorial Day", 5, "Monday", -1),
        ("fathers-day", "Father's Day", 6, "Sunday", 3),
        ("labor-day", "Labor Day", 9, "Monday", 1),
        ("columbus-indigenous-day", "Columbus Day / Indigenous Peoples' Day", 10, "Monday", 2),
        ("thanksgiving", "Thanksgiving", 11, "Thursday", 4),
    )
    for id, name, month, weekday, occurrence in weekday_rules:
        day = _nth_weekday(month, weekday, occurrence)
        items.append(
            _fixed(
                id,
                name,
                "civic",
                month,
                day,
                ("StillPoint fixed civic recurrence registry",),
                rule="fixed_result_of_weekday_ordinal_at_ratification",
            )
        )

    for quarter, ordinal in enumerate((91, 182, 273, 364), start=1):
        month, day = month_day_from_ordinal(ordinal)
        items.append(
            _fixed(
                f"season-gate-{quarter}",
                f"Season Gate {quarter}",
                "season-gate",
                month,
                day,
                ENOCHIC_SOURCES,
                rule="fixed_91_day_quarter_gate",
            )
        )

    return tuple(sorted(items, key=lambda item: (item.ordinal, item.id)))


def annual_day(ordinal: int) -> dict[str, Any]:
    address = common_date(
        year=1,
        ordinal=ordinal,
        day001_weekday=DAY001_WEEKDAY,
    )
    phase = phase_for_base_day(ordinal)
    observances = [
        item.id
        for item in resolved_observances()
        if item.ordinal == ordinal
    ]
    return {
        "ordinal": ordinal,
        "month": address.month,
        "day": address.day,
        "weekday": address.weekday,
        "week": address.week,
        "dayInWeek": address.day_in_week,
        "quarter": address.quarter,
        "quarterDay": address.day_of_quarter,
        "enochPhase": phase.phase,
        "enochGate": phase.gate,
        "sabbath": address.weekday == "Saturday",
        "observances": observances,
    }


def address_for(
    *,
    year: int,
    month: int,
    day: int,
    first_cycle_year: int = 1,
) -> dict[str, Any]:
    ordinal = ordinal_day(month, day)
    annual = annual_day(ordinal)
    jubilee = jubilee_state(
        common_year=year,
        epoch_common_year=first_cycle_year,
        epoch_cycle=1,
    )
    return {
        "year": year,
        **annual,
        "jubilee": None if jubilee is None else {
            "cycle": jubilee.cycle,
            "cycleYear": jubilee.cycle_year,
            "sevenYearBlock": jubilee.seven_year_block,
            "yearWithinBlock": jubilee.year_within_block,
            "isSabbaticalThreshold": jubilee.is_sabbatical_threshold,
            "isJubileeYear": jubilee.is_jubilee_year,
        },
        "provenance": {
            "grid": "StillPoint fixed 364-day enactment",
            "weeklySabbath": "Leviticus 23:3",
            "enochicArchitecture": list(ENOCHIC_SOURCES),
        },
    }


def build_sacred_civic_map(
    *,
    first_year: int = 1,
    year_count: int = DEFAULT_CYCLE_YEARS,
) -> dict[str, Any]:
    if year_count != 50:
        raise ValueError("canonical StillPoint map is exactly fifty years")

    observances = resolved_observances()
    years: list[dict[str, Any]] = []
    for year in range(first_year, first_year + year_count):
        state = jubilee_state(
            common_year=year,
            epoch_common_year=first_year,
            epoch_cycle=1,
        )
        assert state is not None
        years.append(
            {
                "year": year,
                "cycle": state.cycle,
                "cycleYear": state.cycle_year,
                "sevenYearBlock": state.seven_year_block,
                "yearWithinBlock": state.year_within_block,
                "isSabbaticalThreshold": state.is_sabbatical_threshold,
                "isJubileeYear": state.is_jubilee_year,
                "jubileeReleaseGateOrdinal": ordinal_day(7, 10)
                if state.is_jubilee_year
                else None,
                "sources": (
                    ["Leviticus 25:8-13"]
                    if state.is_jubilee_year
                    else ["Leviticus 25:1-7", "Deuteronomy 15:1-18"]
                    if state.is_sabbatical_threshold
                    else []
                ),
            }
        )

    return {
        "version": MAP_VERSION,
        "authorityStatus": "ratified-fixed-grid",
        "truthCondition": (
            "StillPoint maps the Abrahamic/scriptural witnesses as evidence of "
            "the underlying sacred architecture of time; it does not claim "
            "civil or astronomical systems possess authority to move the grid."
        ),
        "annualGrid": {
            "days": 364,
            "weeks": 52,
            "monthLengths": list(MONTH_LENGTHS),
            "firstDate": {"month": 1, "day": 1},
            "lastDate": {"month": 12, "day": 30},
            "december31Exists": False,
            "day001Weekday": DAY001_WEEKDAY,
            "directTransition": "12-30 -> next-year 01-01",
        },
        "sourceArchitecture": {
            "quarterDays": 91,
            "quarters": 4,
            "enochPhaseLengths": list(PHASE_LENGTHS),
            "enochGateSequence": list(GATE_SEQUENCE),
            "witnesses": list(ENOCHIC_SOURCES),
        },
        "observances": [item.as_dict() for item in observances],
        "annualTemplate": [annual_day(ordinal) for ordinal in range(1, 365)],
        "years": years,
    }


def export_sacred_civic_map(
    path: Path,
    *,
    first_year: int = 1,
) -> None:
    path.write_text(
        json.dumps(
            build_sacred_civic_map(first_year=first_year),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
