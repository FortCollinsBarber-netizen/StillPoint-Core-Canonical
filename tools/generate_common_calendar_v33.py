#!/usr/bin/env python3
"""Historical v3.3 reconciliation compiler marker.

The v3.3 model is retained for provenance and regression history only.
It is not an operative Calendar Core publication path after immutable v2
ratification.
"""

from __future__ import annotations


class SupersededCalendarModelError(RuntimeError):
    pass


def generate(*args, **kwargs):
    raise SupersededCalendarModelError(
        "Temporal v3.3 Reconciliation is superseded and non-operative; "
        "use generate_common_calendar_v2.py for the immutable 364-day map"
    )


def main() -> None:
    raise SystemExit(
        "Temporal v3.3 Reconciliation is historical only. "
        "Use tools/generate_common_calendar_v2.py."
    )


if __name__ == "__main__":
    main()
