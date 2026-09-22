"""Witness and larger-cycle layers that observe or annotate Calendar Core.

These modules may consume Common Calendar coordinates. They do not redefine the
364-day ordinary year, the seven-day sequence, or publication authority.
"""

from .jubilee import jubilee_state

__all__ = ["jubilee_state"]
