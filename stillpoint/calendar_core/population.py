from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Iterator

from .calendar import common_date, ordinal_day
from .gates import phase_for_base_day
from .governor import (
    CanonicalDate,
    RHYTHM_GOVERNOR,
    RhythmAuthority,
    RhythmRequest,
)
from .jubilee import jubilee_state
from .observances import observances_for_ordinal
from .publication import validate_publication_document


@dataclass(frozen=True)
class PopulationAddress:
    year: int
    month: int
    day: int
    ordinal: int
    week: int
    day_in_week: int
    weekday: str
    quarter: int
    day_of_quarter: int
    enoch_phase: int
    enoch_gate: int
    enoch_motion: str
    is_sabbath_date: bool
    observance_ids: tuple[str, ...]
    observance_names: tuple[str, ...]
    source_refs: tuple[str, ...]
    jubilee_cycle: int | None
    jubilee_year: int | None
    is_sabbatical_threshold: bool
    is_jubilee_year: bool
    is_jubilee_release_day: bool
    opening_civil_date: date
    closes_on_civil_date: date

    @property
    def calendar_address(self) -> str:
        return f"Y_{self.year}-{self.ordinal:03d}"


def _validated_rows(
    publication_document: dict[str, Any],
) -> list[dict[str, Any]]:
    validate_publication_document(publication_document)
    rows = publication_document.get("years")
    if not isinstance(rows, list):
        raise ValueError("validated publication must contain year rows")
    return rows


def _row_for_year(
    publication_document: dict[str, Any],
    year: int,
) -> dict[str, Any]:
    for row in _validated_rows(publication_document):
        if int(row["year"]) == year:
            return row
    raise ValueError(f"year {year} is outside the finite publication")


def address(
    *,
    publication_document: dict[str, Any],
    year: int,
    month: int,
    day: int,
    jubilee_epoch_common_year: int | None = None,
    jubilee_epoch_cycle: int = 1,
) -> PopulationAddress:
    row = _row_for_year(publication_document, year)
    ordinal = ordinal_day(month, day)
    current = common_date(year=year, ordinal=ordinal)
    phase = phase_for_base_day(ordinal)
    observances = observances_for_ordinal(ordinal)
    RHYTHM_GOVERNOR.require(
        RhythmRequest(
            authority=RhythmAuthority.OVERLAY,
            source="calendar-population",
            canonical_date=CanonicalDate(year, month, day),
            annotation={
                "observance_ids": [item.id for item in observances],
                "season_gate": phase.gate,
                "season_phase": phase.phase,
            },
        )
    )

    source_refs: list[str] = [
        "1 Enoch 72-82",
        "Jubilees 6:29-32",
    ]
    for observance in observances:
        for ref in observance.source_refs:
            if ref not in source_refs:
                source_refs.append(ref)

    is_sabbath_date = current.weekday == "Saturday"
    if is_sabbath_date:
        for ref in (
            "Exodus 20:8-11",
            "Leviticus 23:3",
            "Numbers 28:9-10",
        ):
            if ref not in source_refs:
                source_refs.append(ref)

    jubilee = jubilee_state(
        common_year=year,
        epoch_common_year=jubilee_epoch_common_year,
        epoch_cycle=jubilee_epoch_cycle,
    )

    is_sabbatical = bool(
        jubilee and jubilee.is_sabbatical_threshold
    )
    is_jubilee = bool(
        jubilee and jubilee.is_jubilee_year
    )
    is_release = (
        is_jubilee
        and month == 7
        and day == 10
    )

    if is_sabbatical:
        for ref in (
            "Leviticus 25:1-7",
            "Deuteronomy 15:1-18",
        ):
            if ref not in source_refs:
                source_refs.append(ref)
    if is_jubilee:
        if "Leviticus 25:8-24" not in source_refs:
            source_refs.append("Leviticus 25:8-24")
    if is_release:
        if "Leviticus 25:8-13" not in source_refs:
            source_refs.append("Leviticus 25:8-13")

    opening = date.fromisoformat(
        str(row["openingCivilDate"])
    ) + timedelta(days=ordinal - 1)

    return PopulationAddress(
        year=year,
        month=month,
        day=day,
        ordinal=ordinal,
        week=current.week,
        day_in_week=current.day_in_week,
        weekday=current.weekday,
        quarter=current.quarter,
        day_of_quarter=current.day_of_quarter,
        enoch_phase=phase.phase,
        enoch_gate=phase.gate,
        enoch_motion=phase.motion,
        is_sabbath_date=is_sabbath_date,
        observance_ids=tuple(
            item.id for item in observances
        ),
        observance_names=tuple(
            item.name for item in observances
        ),
        source_refs=tuple(source_refs),
        jubilee_cycle=(
            jubilee.cycle if jubilee else None
        ),
        jubilee_year=(
            jubilee.cycle_year if jubilee else None
        ),
        is_sabbatical_threshold=is_sabbatical,
        is_jubilee_year=is_jubilee,
        is_jubilee_release_day=is_release,
        opening_civil_date=opening,
        closes_on_civil_date=opening + timedelta(days=1),
    )


def address_from_ordinal(
    *,
    publication_document: dict[str, Any],
    year: int,
    ordinal: int,
    jubilee_epoch_common_year: int | None = None,
    jubilee_epoch_cycle: int = 1,
) -> PopulationAddress:
    current = common_date(
        year=year,
        ordinal=ordinal,
    )
    return address(
        publication_document=publication_document,
        year=year,
        month=current.month,
        day=current.day,
        jubilee_epoch_common_year=jubilee_epoch_common_year,
        jubilee_epoch_cycle=jubilee_epoch_cycle,
    )


def iter_year(
    *,
    publication_document: dict[str, Any],
    year: int,
    jubilee_epoch_common_year: int | None = None,
    jubilee_epoch_cycle: int = 1,
) -> Iterator[PopulationAddress]:
    for ordinal in range(1, 365):
        yield address_from_ordinal(
            publication_document=publication_document,
            year=year,
            ordinal=ordinal,
            jubilee_epoch_common_year=jubilee_epoch_common_year,
            jubilee_epoch_cycle=jubilee_epoch_cycle,
        )


def iter_fifty_year_map(
    *,
    publication_document: dict[str, Any],
    jubilee_epoch_common_year: int | None = None,
    jubilee_epoch_cycle: int = 1,
) -> Iterator[PopulationAddress]:
    rows = _validated_rows(publication_document)
    if len(rows) != 50:
        raise ValueError(
            "canonical fifty-year map requires exactly 50 publication rows"
        )
    for row in rows:
        yield from iter_year(
            publication_document=publication_document,
            year=int(row["year"]),
            jubilee_epoch_common_year=jubilee_epoch_common_year,
            jubilee_epoch_cycle=jubilee_epoch_cycle,
        )
