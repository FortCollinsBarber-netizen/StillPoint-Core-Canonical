from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .calendar import ordinal_day
from .models import JubileeState
from .sacred import common_from_sacred, DEFAULT_SACRED_PROFILE, sacred_ordinal


@dataclass(frozen=True)
class JubileeReleaseGate:
    """A downstream appointed-time gate; it has no annual-calendar authority."""

    month: int = 7
    day: int = 10
    name: str = "Day of Atonement"
    source_calendar: str = "schematic-enochic-364"
    profile_id: str = DEFAULT_SACRED_PROFILE.id

    @property
    def ordinal(self) -> int:
        """Source-calendar ordinal, never an implicit Common date."""
        return sacred_ordinal(self.month, self.day)

    @property
    def common_month_day(self) -> tuple[int, int]:
        projected = common_from_sacred(2026, self.month, self.day)
        return projected.month, projected.day

    @property
    def common_ordinal(self) -> int:
        return ordinal_day(*self.common_month_day)


def jubilee_state(
    *,
    common_year: int,
    epoch_common_year: Optional[int],
    epoch_cycle: int = 1,
    rollover_rule: str = "overlap-49",
) -> Optional[JubileeState]:
    """Return Jubilee position only when an epoch is explicitly configured.

    The Jubilee counter is downstream of Calendar Core annual law. It never
    chooses an opening, changes a year length, inserts Reconciliation, or
    modifies weekday identity.
    """
    if rollover_rule not in {"overlap-49", "standalone-50"}:
        raise ValueError("unsupported Jubilee rollover rule")
    if epoch_common_year is None:
        return None
    if common_year < epoch_common_year:
        return None
    if epoch_cycle < 1:
        raise ValueError("epoch_cycle must be >= 1")

    years_since = common_year - epoch_common_year
    cycle_length = 49 if rollover_rule == "overlap-49" else 50
    cycle = epoch_cycle + (years_since // cycle_length)
    cycle_year = (years_since % cycle_length) + 1
    is_jubilee = (
        years_since > 0 and years_since % 49 == 0
        if rollover_rule == "overlap-49" else cycle_year == 50
    )

    if rollover_rule == "standalone-50" and cycle_year == 50:
        return JubileeState(
            cycle=cycle,
            cycle_year=50,
            seven_year_block=None,
            year_within_block=None,
            is_sabbatical_threshold=False,
            is_jubilee_year=True,
            rollover_rule=rollover_rule,
            proclamation_ordinal_year=50,
            completed_cycle=cycle,
        )

    block = ((cycle_year - 1) // 7) + 1
    within = ((cycle_year - 1) % 7) + 1
    return JubileeState(
        cycle=cycle,
        cycle_year=cycle_year,
        seven_year_block=block,
        year_within_block=within,
        is_sabbatical_threshold=(within == 7),
        is_jubilee_year=is_jubilee,
        rollover_rule=rollover_rule,
        proclamation_ordinal_year=50 if is_jubilee else None,
        completed_cycle=cycle - 1 if is_jubilee else None,
    )


def jubilee_release_gate(
    *,
    common_year: int,
    epoch_common_year: Optional[int],
    epoch_cycle: int = 1,
    rollover_rule: str = "overlap-49",
) -> Optional[JubileeReleaseGate]:
    """Return the Year-50 release gate without granting it annual authority."""
    state = jubilee_state(
        common_year=common_year,
        epoch_common_year=epoch_common_year,
        epoch_cycle=epoch_cycle,
        rollover_rule=rollover_rule,
    )
    if state is None or not state.is_jubilee_year:
        return None
    return JubileeReleaseGate()
