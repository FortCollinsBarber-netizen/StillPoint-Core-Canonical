"""Compatibility imports for the pre-refinement Calendar Core API.

Reference-rule selection is publication policy, not pure Calendar Core law.
New code should import these functions from stillpoint.calendar_publication.
"""

from stillpoint.calendar_publication.compiler import (
    BASE_YEAR_DAYS,
    SPRING_GATE_ORDINAL_V33 as SPRING_GATE_ORDINAL,
    select_v32_nearest_legal,
    select_v33_nearest_spring_gate,
    spring_gate_date,
)

__all__ = [
    "BASE_YEAR_DAYS",
    "SPRING_GATE_ORDINAL",
    "select_v32_nearest_legal",
    "select_v33_nearest_spring_gate",
    "spring_gate_date",
]
