#!/usr/bin/env python3
"""Generate a finite immutable 364-day Common Calendar projection.

This tool does not consult astronomy, lunar phase, seasons, or a Reconciliation
operator. Those may be attached separately as witnesses; none can move the grid.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from stillpoint.calendar_core.publication import (
    PUBLICATION_VERSION,
    PublicationValidationError,
    publication_digest,
    validate_publication_document,
)
from stillpoint.calendar_core.spec import SPEC_VERSION

BASE_YEAR_DAYS = 364


def generate(
    *,
    first_year_label: int,
    first_opening: dt.date,
    count: int = 50,
    authority_id: str = "UNRATIFIED_PILOT",
    authority_status: str = "pilot",
) -> dict[str, Any]:
    if count < 1:
        raise ValueError("count must be >= 1")
    if authority_status not in ("pilot", "enacted"):
        raise ValueError("authority_status must be pilot or enacted")
    if not authority_id.strip():
        raise ValueError("authority_id is required")

    years = [
        {
            "year": first_year_label + offset,
            "openingCivilDate": (
                first_opening
                + dt.timedelta(days=BASE_YEAR_DAYS * offset)
            ).isoformat(),
        }
        for offset in range(count)
    ]

    document: dict[str, Any] = {
        "publicationVersion": PUBLICATION_VERSION,
        "calendarCoreSpecVersion": SPEC_VERSION,
        "authority": {
            "id": authority_id.strip(),
            "status": authority_status,
        },
        "years": years,
    }
    document["publicationDigest"] = publication_digest(document)
    validate_publication_document(document)
    return document


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--first-year-label", type=int, required=True)
    parser.add_argument("--first-opening", type=dt.date.fromisoformat, required=True)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--authority-id", required=True)
    parser.add_argument(
        "--authority-status",
        choices=("pilot", "enacted"),
        default="pilot",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    document = generate(
        first_year_label=args.first_year_label,
        first_opening=args.first_opening,
        count=args.count,
        authority_id=args.authority_id,
        authority_status=args.authority_status,
    )
    args.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
