from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .calendar import (
    boundary_dates_for_common_date,
    ordinal_day,
    weekday_for_ordinal,
)


@dataclass(frozen=True)
class AppointedTime:
    """A supplied observance projected onto Calendar Core law.

    Appointed times are downstream expressions. Creating one cannot alter the
    immutable annual grid, weekday sequence, witness layer, or translation epoch.
    """

    id: str
    name: str
    month: int
    day: int
    opens_at: str = "local-apparent-sunset"
    closes_at: str = "next-local-apparent-sunset"
    authority_status: str = "supplied-downstream"

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("appointed-time id is required")
        if not self.name.strip():
            raise ValueError("appointed-time name is required")
        ordinal_day(self.month, self.day)
        if self.opens_at != "local-apparent-sunset":
            raise ValueError("unsupported appointed-time opening boundary")
        if self.closes_at != "next-local-apparent-sunset":
            raise ValueError("unsupported appointed-time closing boundary")


@dataclass(frozen=True)
class AppointedTimeOccurrence:
    appointed_time: AppointedTime
    common_year: int
    ordinal: int
    weekday: str
    opens_on_civil_date: date
    closes_on_civil_date: date
    calendar_state: str = "ORDINARY"


def project_appointed_time(
    appointed_time: AppointedTime,
    *,
    common_year: int,
    opening_civil_date: date,
    day001_weekday: str,
    calendar_state: str = "ORDINARY",
) -> AppointedTimeOccurrence | None:
    """Project a fixed appointed time only into the immutable ordinary grid."""
    if calendar_state != "ORDINARY":
        return None

    ordinal = ordinal_day(
        appointed_time.month,
        appointed_time.day,
    )
    opens_on, closes_on = boundary_dates_for_common_date(
        opening_civil_date=opening_civil_date,
        month=appointed_time.month,
        day=appointed_time.day,
    )
    return AppointedTimeOccurrence(
        appointed_time=appointed_time,
        common_year=common_year,
        ordinal=ordinal,
        weekday=weekday_for_ordinal(
            ordinal,
            day001_weekday,
        ),
        opens_on_civil_date=opens_on,
        closes_on_civil_date=closes_on,
    )
