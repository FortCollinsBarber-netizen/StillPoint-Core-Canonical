"""Compatibility shim.

Jubilee is a larger release-count witness layer, not Calendar Core address law.
New code should import jubilee_state from stillpoint.calendar_witness.
"""

from stillpoint.calendar_witness import jubilee_state

__all__ = ["jubilee_state"]
