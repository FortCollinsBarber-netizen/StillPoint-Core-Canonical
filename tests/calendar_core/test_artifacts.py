import json
import unittest
from datetime import date

from stillpoint.calendar_core.projection_vectors import (
    PROJECTION_VECTOR_VERSION,
    build_calendar_projection_vectors,
)
from stillpoint.calendar_core.publication import (
    PUBLICATION_VERSION,
    PublicationValidationError,
    publication_digest,
    validate_publication_document,
    validate_publication_rows,
)
from stillpoint.calendar_core.sacred_map import build_sacred_civic_map
from stillpoint.calendar_core.spec import SPEC_VERSION, build_calendar_core_spec


class CalendarArtifactTests(unittest.TestCase):
    def _publication(self):
        document = {
            "publicationVersion": PUBLICATION_VERSION,
            "calendarCoreSpecVersion": SPEC_VERSION,
            "authority": {"id": "PILOT_AUTHORITY", "status": "pilot"},
            "referenceRuleVersion": "fixed-364-v1",
            "referencePoint": {"id": "REFERENCE_TEST"},
            "ephemerisEvidence": {"source": "BOUNDARY_TEST", "sha256": "a" * 64},
            "years": [
                {"year": 7, "openingCivilDate": "2026-01-01", "reconciliationDaysAfterCompletion": 0},
                {"year": 8, "openingCivilDate": "2026-12-31", "reconciliationDaysAfterCompletion": 0},
            ],
        }
        document["publicationDigest"] = publication_digest(document)
        return document

    def test_spec_is_fixed_grid_law(self):
        spec = build_calendar_core_spec()
        self.assertEqual(spec["ordinaryCalendar"]["baseYearDays"], 364)
        self.assertEqual(spec["reconciliation"]["allowedDays"], [0])
        self.assertFalse(spec["grid"]["december31Exists"])
        self.assertEqual(spec["ordinaryCalendar"]["monthLengths"][-1], 30)

    def test_sacred_civic_map_is_one_template_plus_fifty_year_cycle(self):
        doc = build_sacred_civic_map()
        self.assertEqual(len(doc["annualTemplate"]), 364)
        self.assertEqual(len(doc["years"]), 50)
        self.assertEqual((doc["annualTemplate"][-1]["month"], doc["annualTemplate"][-1]["day"]), (12, 30))

    def test_projection_vectors_have_no_reconciliation_state(self):
        doc = build_calendar_projection_vectors()
        self.assertEqual(doc["version"], PROJECTION_VECTOR_VERSION)
        self.assertTrue(doc["vectors"])
        self.assertTrue(all(row["reconciliationDaysAfterCompletion"] == 0 for row in doc["vectors"]))
        self.assertTrue(all(row["expected"]["state"] == "ORDINARY" for row in doc["vectors"]))

    def test_publication_rows_are_exactly_364_days_apart(self):
        result = validate_publication_rows([
            {"year": 7, "openingCivilDate": "2026-01-01", "reconciliationDaysAfterCompletion": 0},
            {"year": 8, "openingCivilDate": "2026-12-31", "reconciliationDaysAfterCompletion": 0},
        ])
        self.assertEqual(result.first_opening, date(2026, 1, 1))
        self.assertEqual(result.year_count, 2)

    def test_publication_rejects_any_reconciliation(self):
        with self.assertRaises(PublicationValidationError) as raised:
            validate_publication_rows([
                {"year": 7, "openingCivilDate": "2026-01-01", "reconciliationDaysAfterCompletion": 7}
            ])
        self.assertEqual(raised.exception.code, "INVALID_RECONCILIATION")

    def test_publication_envelope_binds_finite_translation_evidence(self):
        envelope = validate_publication_document(
            self._publication(),
            authorized_authority_ids={"PILOT_AUTHORITY"},
            require_authority_status="pilot",
            expected_reference_rule_version="fixed-364-v1",
            expected_reference_station_id="REFERENCE_TEST",
            expected_ephemeris_id="BOUNDARY_TEST",
            expected_ephemeris_sha256="a" * 64,
            at_opening=date(2026, 12, 31),
        )
        self.assertEqual(envelope.publication_range.year_count, 2)

    def test_publication_digest_detects_tampering(self):
        document = self._publication()
        document["years"][0]["year"] = 99
        with self.assertRaises(PublicationValidationError) as raised:
            validate_publication_document(document)
        self.assertEqual(raised.exception.code, "PUBLICATION_DIGEST_MISMATCH")

    def test_map_contains_no_old_seven_day_transition(self):
        serialized = json.dumps(build_sacred_civic_map())
        self.assertNotIn('"reconciliationDaysAfterCompletion": 7', serialized)


if __name__ == "__main__":
    unittest.main()
