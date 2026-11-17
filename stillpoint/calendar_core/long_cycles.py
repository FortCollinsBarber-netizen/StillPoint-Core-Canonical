"""Explicit cycle configuration and arithmetic comparison, never release authority.

The operational counter implements standalone fiftieth years. Consecutive
49-year blocks are compared here without deciding how a proclamation overlays
them or translating a sacred appointment to a Common Calendar date.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import lcm
from typing import Any

from .jubilee import jubilee_state


def _positive_integer(value: object, name: str) -> None:
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True)
class JubileeConfiguration:
    """Caller-selected calculation inputs, not proof of adopted civic policy.

    An explicit None epoch requests no designation. Only the existing counter
    is operationally supported; comparing a 49-year model does not enable it.
    """

    epoch_common_year: int | None
    epoch_cycle: int = 1
    rollover_rule: str = "standalone-50"

    def __post_init__(self) -> None:
        if self.epoch_common_year is not None:
            _positive_integer(self.epoch_common_year, "epoch_common_year")
        _positive_integer(self.epoch_cycle, "epoch_cycle")
        if self.rollover_rule != "standalone-50":
            raise ValueError("operational rollover_rule supports standalone-50 only")


def compare_long_cycles(
    *, common_year: int, epoch_common_year: int | None, epoch_cycle: int = 1,
) -> dict[str, Any]:
    """Compare phases under stated inputs; do not designate an operative rule.

    The phase origin is the beginning of epoch Year 1, so epoch + 49 is the
    beginning of ordinal Year 50. Priestly phase assumes 52 weeks per year
    and 24 uninterrupted weekly courses. No seasonal correction is applied.
    This calculation does not extend any finite calendar publication.
    """
    _positive_integer(common_year, "common_year")
    _positive_integer(epoch_cycle, "epoch_cycle")
    if epoch_common_year is not None:
        _positive_integer(epoch_common_year, "epoch_common_year")
    result: dict[str, Any] = {
        "scope": "arithmetic-comparison-only",
        "grid_authority": False,
        "release_authority": False,
        "common_year": common_year,
        "epoch_common_year": epoch_common_year,
        "standalone_counter_epoch_cycle": epoch_cycle,
        "assumptions": {"year_days": 364, "weeks_per_year": 52, "weekly_courses": 24},
        "recurrence_years": {
            "six_seven_forty_nine": lcm(6, 7, 49),
            "with_independent_fifty": lcm(6, 7, 49, 50),
        },
        "status": "unconfigured-epoch",
        "models": None,
    }
    if epoch_common_year is None:
        return result
    if common_year < epoch_common_year:
        result["status"] = "before-epoch"
        return result

    elapsed = common_year - epoch_common_year
    fifty = jubilee_state(common_year=common_year, epoch_common_year=epoch_common_year,
                         epoch_cycle=epoch_cycle)
    result.update({
        "status": "comparison-only",
        "elapsed_years": elapsed,
        "ordinal_year_from_epoch": elapsed + 1,
        "models": {
            "continuous_seven_year": {"year": elapsed % 7 + 1},
            "six_year_priestly": {
                "year": elapsed % 6 + 1,
                "course_phase_at_year_start_zero_based": (elapsed * 52) % 24,
            },
            "consecutive_forty_nine_year_blocks": {
                "block_from_epoch": elapsed // 49 + 1,
                "year": elapsed % 49 + 1,
                "completed_blocks": elapsed // 49,
                "at_boundary_after_origin": elapsed > 0 and elapsed % 49 == 0,
                "proclamation_rule": "unresolved",
            },
            "existing_standalone_fifty_year_counter": asdict(fifty),
        },
        "at_294_year_return_after_origin": elapsed > 0 and elapsed % 294 == 0,
    })
    return result
