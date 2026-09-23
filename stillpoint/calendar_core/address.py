from __future__ import annotations

from dataclasses import dataclass
import re

ORDINARY_RE = re.compile(
    r"^Y_(?P<year>-?\d+)-(?P<ordinal>\d{3})$"
)


@dataclass(frozen=True)
class CalendarAddress:
    kind: str
    year: int
    ordinal: int | None = None
    reconciliation_day: int | None = None

    def __post_init__(self) -> None:
        if self.kind != "ORDINARY":
            raise ValueError(
                "ratified Calendar Core addresses are ORDINARY only"
            )
        if self.ordinal is None or not 1 <= self.ordinal <= 364:
            raise ValueError(
                "ordinary address ordinal must be within 1..364"
            )
        if self.reconciliation_day is not None:
            raise ValueError(
                "reconciliation addresses are prohibited"
            )

    @property
    def text(self) -> str:
        assert self.ordinal is not None
        return format_ordinary_address(
            self.year,
            self.ordinal,
        )


def format_ordinary_address(
    year: int,
    ordinal: int,
) -> str:
    if not 1 <= ordinal <= 364:
        raise ValueError(
            "ordinary address ordinal must be within 1..364"
        )
    return f"Y_{year}-{ordinal:03d}"


def format_reconciliation_address(
    year: int,
    reconciliation_day: int,
) -> str:
    del year, reconciliation_day
    raise ValueError(
        "Reconciliation is not part of ratified Common Calendar law"
    )


def parse_calendar_address(
    value: str,
) -> CalendarAddress:
    ordinary = ORDINARY_RE.fullmatch(value)
    if ordinary is not None:
        year = int(ordinary.group("year"))
        ordinal = int(ordinary.group("ordinal"))
        return CalendarAddress(
            kind="ORDINARY",
            year=year,
            ordinal=ordinal,
        )

    raise ValueError(
        f"invalid ratified Calendar Core address: {value!r}"
    )
