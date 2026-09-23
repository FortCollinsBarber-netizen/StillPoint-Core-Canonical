import unittest

from stillpoint.calendar_core.publication import (
    PublicationValidationError,
    validate_publication_rows,
)


class SupersededV33Tests(unittest.TestCase):
    def test_active_grid_rejects_old_seven_day_reconciliation(self):
        with self.assertRaises(PublicationValidationError) as raised:
            validate_publication_rows([
                {
                    "year": 2026,
                    "openingCivilDate": "2026-01-01",
                    "reconciliationDaysAfterCompletion": 7,
                }
            ])
        self.assertEqual(raised.exception.code, "INVALID_RECONCILIATION")

    def test_fixed_years_open_exactly_364_days_apart(self):
        result = validate_publication_rows([
            {
                "year": 2026,
                "openingCivilDate": "2026-01-01",
                "reconciliationDaysAfterCompletion": 0,
            },
            {
                "year": 2027,
                "openingCivilDate": "2026-12-31",
                "reconciliationDaysAfterCompletion": 0,
            },
        ])
        self.assertEqual(result.year_count, 2)


if __name__ == "__main__":
    unittest.main()
