import copy
import unittest

from stillpoint.calendar_core.spec import (
    SPEC_VERSION,
    CalendarSpecValidationError,
    build_calendar_core_spec,
    validate_calendar_core_spec,
)


class CalendarCoreSpecValidationTests(unittest.TestCase):
    def test_supported_fixed_grid_validates_exactly(self):
        spec = build_calendar_core_spec()
        validate_calendar_core_spec(spec)
        self.assertEqual(spec["version"], SPEC_VERSION)
        self.assertEqual(spec["grid"]["status"], "ratified-fixed")
        self.assertEqual(spec["grid"]["days"], 364)
        self.assertEqual(spec["grid"]["weeks"], 52)
        self.assertEqual(spec["grid"]["day001Weekday"], "Thursday")
        self.assertEqual(spec["grid"]["lastDate"], {"month": 12, "day": 30})
        self.assertFalse(spec["grid"]["december31Exists"])
        self.assertEqual(spec["reconciliation"]["allowedDays"], [0])
        self.assertFalse(spec["reconciliation"]["enabled"])

    def test_unknown_spec_version_fails_closed(self):
        spec = build_calendar_core_spec()
        spec["version"] = "future-calendar-law"
        with self.assertRaises(CalendarSpecValidationError) as raised:
            validate_calendar_core_spec(spec)
        self.assertEqual(raised.exception.code, "UNSUPPORTED_SPEC_VERSION")

    def test_structural_drift_fails_closed(self):
        spec = build_calendar_core_spec()
        spec["ordinaryCalendar"]["baseYearDays"] = 365
        with self.assertRaises(CalendarSpecValidationError) as raised:
            validate_calendar_core_spec(spec)
        self.assertEqual(raised.exception.code, "SPEC_DRIFT")

    def test_external_ephemeris_cannot_rewrite_calendar_law(self):
        spec = copy.deepcopy(build_calendar_core_spec())
        spec["ephemerisEvidence"] = {"source": "EXAMPLE", "sha256": "0" * 64}
        with self.assertRaises(CalendarSpecValidationError) as raised:
            validate_calendar_core_spec(spec)
        self.assertEqual(raised.exception.code, "SPEC_CONTAINS_EXTERNAL_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
