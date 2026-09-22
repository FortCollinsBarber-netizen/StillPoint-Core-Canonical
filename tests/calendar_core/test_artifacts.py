import json
import unittest
from datetime import date

from stillpoint.calendar_core.projection_vectors import PROJECTION_VECTOR_VERSION, build_calendar_projection_vectors
from stillpoint.calendar_core.publication import (
    PUBLICATION_VERSION,
    PublicationValidationError,
    publication_digest,
    validate_publication_document,
    validate_publication_rows,
)
from stillpoint.calendar_core.spec import SPEC_VERSION, build_calendar_core_spec


class CalendarArtifactTests(unittest.TestCase):
    def _publication(self):
        document = {
            "publicationVersion": PUBLICATION_VERSION,
            "calendarCoreSpecVersion": SPEC_VERSION,
            "authority": {
                "id": "PILOT_AUTHORITY",
                "status": "pilot",
            },
            "referenceRuleVersion": "v3.3-candidate",
            "referencePoint": {
                "id": "REFERENCE_TEST",
            },
            "ephemerisEvidence": {
                "source": "TEST_EPHEMERIS",
                "sha256": "a" * 64,
            },
            "years": [
                {
                    "year": 7,
                    "openingCivilDate": "2026-01-01",
                    "reconciliationDaysAfterCompletion": 7,
                },
                {
                    "year": 8,
                    "openingCivilDate": "2027-01-07",
                    "reconciliationDaysAfterCompletion": 0,
                },
            ],
        }
        document["publicationDigest"] = publication_digest(document)
        return document

    def test_spec_is_law_not_pilot_fixture(self):
        spec = build_calendar_core_spec()
        self.assertEqual(spec["version"], SPEC_VERSION)
        self.assertEqual(spec["ordinaryCalendar"]["baseYearDays"], 364)
        self.assertEqual(spec["reconciliation"]["allowedDays"], [0, 7])
        self.assertFalse(spec["reconciliation"]["inheritsOrdinaryFields"])
        serialized = json.dumps(spec)
        self.assertNotIn("LOVELAND_TEST", serialized)
        self.assertNotIn("openingCivilDate", serialized)
        self.assertNotIn("jubileeEpoch", serialized)

    def test_projection_vectors_are_conformance_only_and_include_r3(self):
        doc = build_calendar_projection_vectors()
        self.assertEqual(doc["version"], PROJECTION_VECTOR_VERSION)
        self.assertEqual(doc["authorityStatus"], "conformance-only")
        r3 = {row["id"]: row for row in doc["vectors"]}["reconciliation-r3"]["expected"]
        self.assertEqual(r3["continuousK"], 366)
        self.assertEqual(r3["state"], "RECONCILIATION")
        self.assertEqual(r3["reconciliationDay"], 3)
        self.assertEqual(r3["reconciliationAddress"], "Y_2026/Y_2027-R3")
        self.assertIsNone(r3["commonDate"])
        self.assertIsNone(r3["annualPhase"])
        self.assertIsNone(r3["solarGate"])

    def test_publication_rows_are_finite_and_whole_week_only(self):
        rows = [
            {"year": 7, "openingCivilDate": "2026-01-01", "reconciliationDaysAfterCompletion": 7},
            {"year": 8, "openingCivilDate": "2027-01-07", "reconciliationDaysAfterCompletion": 0},
        ]
        result = validate_publication_rows(rows)
        self.assertEqual(result.first_opening, date(2026, 1, 1))
        self.assertEqual(result.year_count, 2)

    def test_publication_rejects_fragmentary_reconciliation(self):
        with self.assertRaises(PublicationValidationError) as raised:
            validate_publication_rows([{"year": 7, "openingCivilDate": "2026-01-01", "reconciliationDaysAfterCompletion": 1}])
        self.assertEqual(raised.exception.code, "INVALID_RECONCILIATION")

    def test_publication_rejects_declared_span_drift(self):
        with self.assertRaises(PublicationValidationError) as raised:
            validate_publication_rows([
                {"year": 7, "openingCivilDate": "2026-01-01", "reconciliationDaysAfterCompletion": 0},
                {"year": 8, "openingCivilDate": "2027-01-01", "reconciliationDaysAfterCompletion": 0},
            ])
        self.assertEqual(raised.exception.code, "OPENING_SPAN_MISMATCH")

    def test_publication_envelope_binds_spec_authority_evidence_and_range(self):
        envelope = validate_publication_document(
            self._publication(),
            authorized_authority_ids={"PILOT_AUTHORITY"},
            require_authority_status="pilot",
            at_opening=date(2027, 1, 7),
        )
        self.assertEqual(envelope.publication_version, PUBLICATION_VERSION)
        self.assertEqual(envelope.calendar_core_spec_version, SPEC_VERSION)
        self.assertEqual(envelope.authority_id, "PILOT_AUTHORITY")
        self.assertEqual(envelope.reference_station_id, "REFERENCE_TEST")
        self.assertEqual(envelope.ephemeris_id, "TEST_EPHEMERIS")
        self.assertEqual(envelope.publication_range.year_count, 2)

    def test_publication_rejects_tampered_content(self):
        document = self._publication()
        document["years"][0]["reconciliationDaysAfterCompletion"] = 0
        with self.assertRaises(PublicationValidationError) as raised:
            validate_publication_document(document)
        self.assertEqual(raised.exception.code, "PUBLICATION_DIGEST_MISMATCH")

    def test_publication_rejects_wrong_calendar_spec_even_with_valid_digest(self):
        document = self._publication()
        document["calendarCoreSpecVersion"] = "future-spec"
        document["publicationDigest"] = publication_digest(document)
        with self.assertRaises(PublicationValidationError) as raised:
            validate_publication_document(document)
        self.assertEqual(raised.exception.code, "UNSUPPORTED_CALENDAR_SPEC_VERSION")

    def test_publication_rejects_unauthorized_authority(self):
        document = self._publication()
        with self.assertRaises(PublicationValidationError) as raised:
            validate_publication_document(
                document,
                authorized_authority_ids={"SOME_OTHER_AUTHORITY"},
            )
        self.assertEqual(raised.exception.code, "UNAUTHORIZED_PUBLICATION_AUTHORITY")

    def test_publication_rejects_authority_status_mismatch(self):
        document = self._publication()
        with self.assertRaises(PublicationValidationError) as raised:
            validate_publication_document(
                document,
                require_authority_status="enacted",
            )
        self.assertEqual(raised.exception.code, "PUBLICATION_AUTHORITY_STATUS_MISMATCH")

    def test_publication_fails_closed_outside_finite_range(self):
        document = self._publication()
        with self.assertRaises(PublicationValidationError) as raised:
            validate_publication_document(
                document,
                at_opening=date(2028, 1, 6),
            )
        self.assertEqual(raised.exception.code, "OUTSIDE_PUBLISHED_RANGE")


if __name__ == "__main__":
    unittest.main()
