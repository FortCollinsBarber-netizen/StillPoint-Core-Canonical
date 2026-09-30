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
            spec["enactmentBoundary"]["status"],
            "annual-law-ratified-epoch-external",
        )
        self.assertTrue(
            spec["enactmentBoundary"]["lawDoesNotSupplyEpoch"]
        )
        self.assertEqual(
            set(spec["enactmentBoundary"]["requiredForFiniteProjection"]),
            {"firstOpening", "publicationAuthority"},
        )
        self.assertEqual(
            spec["annualTransition"],
            {"rule": "DAY_364_TO_NEXT_YEAR_DAY_001"},
        )

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

    def test_pilot_reference_cannot_be_promoted_into_law(self):
        spec = copy.deepcopy(build_calendar_core_spec())
        spec["referencePoint"] = {"id": "GROUND_ZERO"}
        with self.assertRaises(CalendarSpecValidationError) as raised:
            validate_calendar_core_spec(spec)
        self.assertEqual(
            raised.exception.code,
            "SPEC_CONTAINS_ENACTMENT_DATA",
        )

    def test_first_opening_cannot_be_promoted_into_law(self):
        spec = copy.deepcopy(build_calendar_core_spec())
        spec["firstOpening"] = {"openingCivilDate": "2026-01-01"}
        with self.assertRaises(CalendarSpecValidationError) as raised:
            validate_calendar_core_spec(spec)
        self.assertEqual(
            raised.exception.code,
            "SPEC_CONTAINS_ENACTMENT_DATA",
        )

    def test_ephemeris_evidence_cannot_become_law(self):
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
