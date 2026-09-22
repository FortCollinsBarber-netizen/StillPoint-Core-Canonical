from __future__ import annotations

from dataclasses import dataclass
import re

ORDINARY_RE = re.compile(
    r"^Y_(?P<year>-?\d+)-(?P<ordinal>\d{3})$"
)


@dataclass(frozen=True)
class CalendarAddress:
    year: int
    ordinal: int

    def __post_init__(self) -> None:
        if not 1 <= self.ordinal <= 364:
            raise ValueError(
                "calendar address ordinal must be within 1..364"
            )

    @property
    def text(self) -> str:
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
            "calendar address ordinal must be within 1..364"
        )
    return f"Y_{year}-{ordinal:03d}"


def parse_calendar_address(
    value: str,
) -> CalendarAddress:
    ordinary = ORDINARY_RE.fullmatch(
        value
    )
    if ordinary is None:
        raise ValueError(
            (
                "invalid immutable Calendar "
                f"Core address: {value!r}"
            )
        )

    return CalendarAddress(
        year=int(
            ordinary.group("year")
        ),
        ordinal=int(
            ordinary.group("ordinal")
        ),
    )
