from __future__ import annotations

from typing import Optional

from .models import JubileeState


def jubilee_state(
    *,
    common_year: int,
    epoch_common_year: Optional[int],
    epoch_cycle: int = 1,
) -> Optional[JubileeState]:
    """Return Jubilee position only when an epoch is explicitly configured."""
    if epoch_common_year is None:
        return None
    if common_year < epoch_common_year:
        return None
    if epoch_cycle < 1:
        raise ValueError("epoch_cycle must be >= 1")

    years_since = common_year - epoch_common_year
    cycle = epoch_cycle + (years_since // 50)
    cycle_year = (years_since % 50) + 1

    if cycle_year == 50:
        return JubileeState(
            cycle=cycle,
            cycle_year=50,
            seven_year_block=None,
            year_within_block=None,
            is_sabbatical_threshold=False,
            is_jubilee_year=True,
        )

    block = ((cycle_year - 1) // 7) + 1
    within = ((cycle_year - 1) % 7) + 1
    return JubileeState(
        cycle=cycle,
        cycle_year=cycle_year,
        seven_year_block=block,
        year_within_block=within,
        is_sabbatical_threshold=(within == 7),
        is_jubilee_year=False,
    )
