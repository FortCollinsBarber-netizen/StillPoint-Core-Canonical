import copy
import unittest

from stillpoint.calendar_core.spec import (
    SPEC_VERSION,
    CalendarSpecValidationError,
    build_calendar_core_spec,
    validate_calendar_core_spec,
)


class CalendarCoreSpecValidationTests(unittest.TestCase):
    def test_supported_spec_validates_exactly(self):
        spec = build_calendar_core_spec()
        validate_calendar_core_spec(spec)
        self.assertEqual(spec["version"], SPEC_VERSION)
        self.assertEqual(
            spec["ordinaryCalendar"]["monthLengths"],
            [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 30],
        )
        self.assertFalse(
            spec["ordinaryCalendar"]["december31Exists"]
        )
        self.assertEqual(
            spec["canonicalCycle"],
            {
                "firstYearLabel": 2026,
                "firstOpeningCivilDate": "2026-01-01",
                "day001Weekday": "Thursday",
                "yearCount": 50,
                "totalDays": 18200,
                "transition": "12-30->next-year-01-01",
            },
        )
        self.assertEqual(
            spec["reconciliation"]["allowedDays"],
            [0],
        )
        self.assertEqual(
            spec["referenceRules"]["operative"],
            {
                "operator": "Fixed364",
                "status": "ratified",
            },
        )

    def test_unknown_spec_version_fails_closed(self):
        spec = build_calendar_core_spec()
        spec["version"] = "future-calendar-law"
        with self.assertRaises(CalendarSpecValidationError) as raised:
            validate_calendar_core_spec(spec)
        self.assertEqual(
            raised.exception.code,
            "UNSUPPORTED_SPEC_VERSION",
        )

    def test_structural_drift_fails_closed(self):
        spec = build_calendar_core_spec()
        spec["ordinaryCalendar"]["baseYearDays"] = 371
        with self.assertRaises(CalendarSpecValidationError) as raised:
            validate_calendar_core_spec(spec)
        self.assertEqual(
            raised.exception.code,
            "SPEC_DRIFT",
        )

    def test_pilot_reference_cannot_be_promoted_into_law(self):
        spec = copy.deepcopy(build_calendar_core_spec())
        spec["referencePoint"] = {
            "id": "GROUND_ZERO",
        }
        with self.assertRaises(CalendarSpecValidationError) as raised:
            validate_calendar_core_spec(spec)
        self.assertEqual(
            raised.exception.code,
            "SPEC_CONTAINS_ENACTMENT_DATA",
        )

    def test_ephemeris_cannot_be_promoted_into_grid_law(self):
        spec = copy.deepcopy(build_calendar_core_spec())
        spec["ephemerisEvidence"] = {
            "source": "EXAMPLE",
            "sha256": "0" * 64,
        }
        with self.assertRaises(CalendarSpecValidationError) as raised:
            validate_calendar_core_spec(spec)
        self.assertEqual(
            raised.exception.code,
            "SPEC_CONTAINS_ENACTMENT_DATA",
        )


if __name__ == "__main__":
    unittest.main()
