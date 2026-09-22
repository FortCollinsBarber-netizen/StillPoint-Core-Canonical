from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterator

from .calendar import (
    BASE_YEAR_DAYS,
    MONTH_LENGTHS,
    common_date,
    ordinal_day,
)
from .gates import phase_for_base_day
from .jubilee import jubilee_state
from .observances import observances_for_ordinal

FIRST_YEAR_LABEL = 2026
YEAR_COUNT = 50
LAST_YEAR_LABEL = FIRST_YEAR_LABEL + YEAR_COUNT - 1
FIRST_OPENING_CIVIL_DATE = date(2026, 1, 1)
DAY001_WEEKDAY = "Thursday"
TOTAL_DAYS = BASE_YEAR_DAYS * YEAR_COUNT


@dataclass(frozen=True)
class CanonicalAddress:
    year: int
    month: int
    day: int
    ordinal: int
    week: int
    day_in_week: int
    weekday: str
    season: int
    day_of_season: int
    enoch_phase: int
    enoch_gate: int
    enoch_motion: str
    is_sabbath: bool
    observance_ids: tuple[str, ...]
    observance_names: tuple[str, ...]
    provenance: tuple[str, ...]
    jubilee_cycle: int
    jubilee_year: int
    is_sabbatical_threshold: bool
    is_jubilee_year: bool
    is_jubilee_release_day: bool
    opening_civil_date: date
    closes_on_civil_date: date

    @property
    def calendar_address(self) -> str:
        return f"Y_{self.year}-{self.ordinal:03d}"


def validate_canonical_map() -> None:
    if sum(MONTH_LENGTHS) != BASE_YEAR_DAYS:
        raise RuntimeError("canonical month surface must total 364 days")
    if BASE_YEAR_DAYS != 52 * 7:
        raise RuntimeError("canonical year must equal 52 exact weeks")
    if TOTAL_DAYS != 18_200:
        raise RuntimeError("50-year map must contain exactly 18,200 days")
    try:
        ordinal_day(12, 31)
    except ValueError:
        pass
    else:
        raise RuntimeError("December 31 must not exist")


def year_opening_civil_date(year: int) -> date:
    validate_canonical_map()
    if not FIRST_YEAR_LABEL <= year <= LAST_YEAR_LABEL:
        raise ValueError(
            f"year must be within {FIRST_YEAR_LABEL}..{LAST_YEAR_LABEL}"
        )
    return FIRST_OPENING_CIVIL_DATE + timedelta(
        days=(year - FIRST_YEAR_LABEL) * BASE_YEAR_DAYS
    )


def address(
    *,
    year: int,
    month: int,
    day: int,
) -> CanonicalAddress:
    opening = year_opening_civil_date(year)
    ordinal = ordinal_day(month, day)
    common = common_date(
        year=year,
        ordinal=ordinal,
        day001_weekday=DAY001_WEEKDAY,
    )
    phase = phase_for_base_day(ordinal)
    jubilee = jubilee_state(
        common_year=year,
        epoch_common_year=FIRST_YEAR_LABEL,
        epoch_cycle=1,
    )
    assert jubilee is not None

    observances = observances_for_ordinal(ordinal)
    provenance: list[str] = []
    for observance in observances:
        for ref in observance.source_refs:
            if ref not in provenance:
                provenance.append(ref)

    release_day = (
        jubilee.is_jubilee_year
        and month == 7
        and day == 10
    )
    if release_day:
        for ref in ("Leviticus 25:8-13",):
            if ref not in provenance:
                provenance.append(ref)

    civil_open = opening + timedelta(days=ordinal - 1)

    return CanonicalAddress(
        year=year,
        month=month,
        day=day,
        ordinal=ordinal,
        week=common.week,
        day_in_week=common.day_in_week,
        weekday=common.weekday,
        season=common.quarter,
        day_of_season=common.day_of_quarter,
        enoch_phase=phase.phase,
        enoch_gate=phase.gate,
        enoch_motion=phase.motion,
        is_sabbath=(common.weekday == "Saturday"),
        observance_ids=tuple(o.id for o in observances),
        observance_names=tuple(o.name for o in observances),
        provenance=tuple(provenance),
        jubilee_cycle=jubilee.cycle,
        jubilee_year=jubilee.cycle_year,
        is_sabbatical_threshold=jubilee.is_sabbatical_threshold,
        is_jubilee_year=jubilee.is_jubilee_year,
        is_jubilee_release_day=release_day,
        opening_civil_date=civil_open,
        closes_on_civil_date=civil_open + timedelta(days=1),
    )


def address_from_ordinal(
    *,
    year: int,
    ordinal: int,
) -> CanonicalAddress:
    common = common_date(
        year=year,
        ordinal=ordinal,
        day001_weekday=DAY001_WEEKDAY,
    )
    return address(
        year=year,
        month=common.month,
        day=common.day,
    )


def address_from_continuous_offset(
    offset: int,
) -> CanonicalAddress:
    validate_canonical_map()
    if not 0 <= offset < TOTAL_DAYS:
        raise ValueError("offset is outside the ratified 50-year map")
    year_offset, day_offset = divmod(offset, BASE_YEAR_DAYS)
    return address_from_ordinal(
        year=FIRST_YEAR_LABEL + year_offset,
        ordinal=day_offset + 1,
    )


def iter_year(year: int) -> Iterator[CanonicalAddress]:
    for ordinal in range(1, BASE_YEAR_DAYS + 1):
        yield address_from_ordinal(
            year=year,
            ordinal=ordinal,
        )


def iter_fifty_year_map() -> Iterator[CanonicalAddress]:
    for year in range(FIRST_YEAR_LABEL, LAST_YEAR_LABEL + 1):
        yield from iter_year(year)
