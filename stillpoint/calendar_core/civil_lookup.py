"""Read-only public Gregorian-date lookup into the enacted Common Calendar.

An external Gregorian date is a *translation input*, never a new authority for
the 364-day Common grid. This feature uses only the already-public finite
publication and current Calendar Core projection; it has no provider, network,
company database, personal data, or private-repository dependency.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
import re
from typing import Any

from .runtime_surface import calendar_day_payload, load_enacted_publication

LOOKUP_SCHEMA = "stillpoint.civil-date-lookup.v1"
DAYS_PER_YEAR = 364


def _civil_date(value: str | date) -> date:
    if type(value) is date:
        return value
    if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
        raise ValueError("civil date must be exactly YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("civil date is not a valid Gregorian date") from exc


def civil_date_lookup_payload(civil_date: str | date) -> dict[str, Any]:
    """Resolve an external civil date to one and only one published Common day.

    The publication's signed/validated annual opening rows are the sole source
    for alignment. Arithmetic only locates an existing year/ordinal; the
    established Calendar Core then constructs the actual read-only day payload.
    No reverse lookup can extend the published 2026–2075 Common-year range.
    """
    requested = _civil_date(civil_date)
    document = load_enacted_publication()
    rows = document["years"]
    first_opening = date.fromisoformat(rows[0]["openingCivilDate"])
    elapsed_days = (requested - first_opening).days
    if elapsed_days < 0 or elapsed_days >= DAYS_PER_YEAR * len(rows):
        raise ValueError("civil date is outside the finite published Calendar projection")

    year_index, ordinal_zero_based = divmod(elapsed_days, DAYS_PER_YEAR)
    row = rows[year_index]
    common_year = int(row["year"])
    day = calendar_day_payload(common_year, ordinal_zero_based + 1)

    # Reject unexpected movement between the document used to locate a date
    # and the document independently loaded by the read-only runtime surface.
    if (
        day["civil_window"]["opens"] != requested.isoformat()
        or day["publication"]["digest"] != document["publicationDigest"]
    ):
        raise ValueError("the public Calendar projection changed during lookup")

    return {
        "schema": LOOKUP_SCHEMA,
        "authority": "read-only-calendar-law",
        "civil_date": requested.isoformat(),
        "translation": {
            "frame": "proleptic-gregorian",
            "role": "external-translation-only",
            "grid_authority": False,
        },
        "calendar_day": day,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="stillpoint-date",
        description="Look up a published StillPoint day from an ordinary YYYY-MM-DD date.",
    )
    parser.add_argument("civil_date", help="External Gregorian date, YYYY-MM-DD")
    args = parser.parse_args(argv)
    try:
        result = civil_date_lookup_payload(args.civil_date)
    except ValueError as exc:
        parser.exit(status=2, message=f"stillpoint-date: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
