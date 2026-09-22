"""Finite calendar publication compiler.

This package binds explicit enacted/pilot authority inputs to versioned
astronomical evidence and produces a finite publication. Evidence supplies
facts; it does not grant itself jurisdiction.
"""

from .compiler import (
    ALLOWED_AUTHORITY_STATUSES,
    BASE_YEAR_DAYS,
    PUBLICATION_VERSION,
    SPRING_GATE_ORDINAL_V33,
    compile_v33_publication,
    publication_digest,
    select_v32_nearest_legal,
    select_v33_nearest_spring_gate,
    spring_gate_date,
    validate_calendar_publication,
)

__all__ = [
    "ALLOWED_AUTHORITY_STATUSES",
    "BASE_YEAR_DAYS",
    "PUBLICATION_VERSION",
    "SPRING_GATE_ORDINAL_V33",
    "compile_v33_publication",
    "publication_digest",
    "select_v32_nearest_legal",
    "select_v33_nearest_spring_gate",
    "spring_gate_date",
    "validate_calendar_publication",
]
