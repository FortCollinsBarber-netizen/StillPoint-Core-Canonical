import unittest

from stillpoint.calendar_core.reconciliation import (
    audit_reconciliation_schedule,
    forecast_reconciliation_weeks,
)


class ReconciliationChecksumTests(unittest.TestCase):
    def test_11_weeks_in_62_years_is_checksum_not_schedule(self):
        self.assertEqual(forecast_reconciliation_weeks(62), 11)
        report = audit_reconciliation_schedule([0] * 51 + [7] * 11)
        self.assertEqual(report.years, 62)
        self.assertEqual(report.actual_weeks, 11)
        self.assertEqual(report.forecast_weeks, 11)

    def test_invalid_partial_week_is_rejected(self):
        with self.assertRaises(ValueError):
            audit_reconciliation_schedule([0, 1, 7])


if __name__ == "__main__":
    unittest.main()
