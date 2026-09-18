from __future__ import annotations

from dataclasses import dataclass

BASE_YEAR_DAYS = 364
MEAN_TROPICAL_YEAR_J2000 = 365.2421897


@dataclass(frozen=True)
class ChecksumReport:
    years: int
    actual_weeks: int
    forecast_weeks: int
    difference_weeks: int


def forecast_reconciliation_weeks(
    years: int,
    *,
    mean_tropical_year: float = MEAN_TROPICAL_YEAR_J2000,
) -> int:
    """Mean-model checksum only. Never use this to choose insertion years."""
    if years < 0:
        raise ValueError("years must be >= 0")
    rate = (mean_tropical_year - BASE_YEAR_DAYS) / 7.0
    return round(years * rate)


def audit_reconciliation_schedule(reconciliation_days: list[int]) -> ChecksumReport:
    if any(value not in (0, 7) for value in reconciliation_days):
        raise ValueError("schedule may contain only 0 or 7 reconciliation days")
    actual = sum(reconciliation_days) // 7
    years = len(reconciliation_days)
    forecast = forecast_reconciliation_weeks(years)
    return ChecksumReport(
        years=years,
        actual_weeks=actual,
        forecast_weeks=forecast,
        difference_weeks=actual - forecast,
    )
