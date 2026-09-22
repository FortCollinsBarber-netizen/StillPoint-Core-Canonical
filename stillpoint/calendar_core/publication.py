from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Sequence

BASE_YEAR_DAYS = 364
ALLOWED_RECONCILIATION_DAYS = (0, 7)


class PublicationValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class PublicationRange:
    first_opening: date
    expires_at_opening: date
    year_count: int


def validate_publication_rows(rows: Sequence[dict[str, Any]]) -> PublicationRange:
    if not rows:
        raise PublicationValidationError(
            "EMPTY_PUBLICATION",
            "publication must contain at least one year row",
        )

    parsed: list[tuple[date, int, int]] = []
    for row in rows:
        try:
            year = int(row["year"])
            opening = date.fromisoformat(str(row["openingCivilDate"]))
            reconciliation = int(row["reconciliationDaysAfterCompletion"])
        except (KeyError, TypeError, ValueError) as exc:
            raise PublicationValidationError(
                "INVALID_PUBLICATION_ROW",
                "publication row is missing a valid year/opening/reconciliation",
            ) from exc

        if reconciliation not in ALLOWED_RECONCILIATION_DAYS:
            raise PublicationValidationError(
                "INVALID_RECONCILIATION",
                "reconciliation must be exactly 0 or 7 days",
            )
        parsed.append((opening, reconciliation, year))

    if parsed != sorted(parsed, key=lambda item: item[0]):
        raise PublicationValidationError(
            "UNSORTED_PUBLICATION",
            "publication rows must be ordered by opening",
        )

    for index in range(len(parsed) - 1):
        opening, reconciliation, year = parsed[index]
        next_opening = parsed[index + 1][0]
        expected = BASE_YEAR_DAYS + reconciliation
        actual = (next_opening - opening).days
        if actual != expected:
            raise PublicationValidationError(
                "OPENING_SPAN_MISMATCH",
                f"year {year} declares {expected} opening-to-opening days; got {actual}",
            )

    last_opening, last_reconciliation, _ = parsed[-1]
    return PublicationRange(
        first_opening=parsed[0][0],
        expires_at_opening=last_opening
        + timedelta(days=BASE_YEAR_DAYS + last_reconciliation),
        year_count=len(parsed),
    )
