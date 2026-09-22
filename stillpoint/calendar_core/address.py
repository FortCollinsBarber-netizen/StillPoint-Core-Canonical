from __future__ import annotations

from dataclasses import dataclass
import re

ORDINARY_RE = re.compile(
    r"^Y_(?P<year>-?\d+)-(?P<ordinal>\d{3})$"
)
RECONCILIATION_RE = re.compile(
    r"^Y_(?P<year>-?\d+)/Y_(?P<next_year>-?\d+)-R(?P<day>[1-7])$"
)


@dataclass(frozen=True)
class CalendarAddress:
    kind: str
    year: int
    ordinal: int | None = None
    reconciliation_day: int | None = None

    def __post_init__(self) -> None:
        if self.kind == "ORDINARY":
            if self.ordinal is None or not 1 <= self.ordinal <= 364:
                raise ValueError(
                    "ordinary address ordinal must be within 1..364"
                )
            if self.reconciliation_day is not None:
                raise ValueError(
                    "ordinary address cannot contain a reconciliation day"
                )
        elif self.kind == "RECONCILIATION":
            if (
                self.reconciliation_day is None
                or not 1 <= self.reconciliation_day <= 7
            ):
                raise ValueError(
                    "reconciliation address day must be within 1..7"
                )
            if self.ordinal is not None:
                raise ValueError(
                    "reconciliation address cannot contain an ordinary ordinal"
                )
        else:
            raise ValueError(
                "calendar address kind must be ORDINARY or RECONCILIATION"
            )

    @property
    def text(self) -> str:
        if self.kind == "ORDINARY":
            assert self.ordinal is not None
            return format_ordinary_address(
                self.year,
                self.ordinal,
            )
        assert self.reconciliation_day is not None
        return format_reconciliation_address(
            self.year,
            self.reconciliation_day,
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
    if not 1 <= reconciliation_day <= 7:
        raise ValueError(
            "reconciliation address day must be within 1..7"
        )
    return (
        f"Y_{year}/Y_{year + 1}"
        f"-R{reconciliation_day}"
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

    reconciliation = RECONCILIATION_RE.fullmatch(
        value
    )
    if reconciliation is not None:
        year = int(reconciliation.group("year"))
        next_year = int(
            reconciliation.group("next_year")
        )
        if next_year != year + 1:
            raise ValueError(
                "reconciliation address must bridge consecutive year labels"
            )
        return CalendarAddress(
            kind="RECONCILIATION",
            year=year,
            reconciliation_day=int(
                reconciliation.group("day")
            ),
        )

    raise ValueError(
        f"invalid Calendar Core address: {value!r}"
    )
