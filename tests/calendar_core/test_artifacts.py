import json
import unittest
from datetime import date

from stillpoint.calendar_core.projection_vectors import (
    PROJECTION_VECTOR_VERSION,
    build_calendar_projection_vectors,
)
from stillpoint.calendar_core.publication import (
    build_projection_semantics,
    PUBLICATION_VERSION,
    PublicationValidationError,
    publication_digest,
    validate_publication_document,
    validate_publication_rows,
)
from stillpoint.calendar_core.spec import (
    SPEC_VERSION,
    build_calendar_core_spec,
)
from stillpoint.calendar_core.witness_overlays import (
    EXTERNAL_WITNESS_ARTIFACT_VERSION,
    build_external_witness_artifact,
)


class CalendarArtifactTests(unittest.TestCase):
    def _publication(self):
        document = {
            "publicationVersion": PUBLICATION_VERSION,
            "calendarCoreSpecVersion": SPEC_VERSION,
            "authority": {
                "id": "PILOT_AUTHORITY",
                "status": "pilot",
            },
            "projectionSemantics": build_projection_semantics(),
            "years": [
                {
                    "year": 1,
                    "openingCivilDate": "2026-01-01",
                },
                {
                    "year": 2,
                    "openingCivilDate": "2026-12-31",
                },
            ],
        }
        document["publicationDigest"] = publication_digest(document)
        return document

    def test_spec_is_immutable_364_day_law(self):
        spec = build_calendar_core_spec()
        self.assertEqual(spec["version"], SPEC_VERSION)
        ordinary = spec["ordinaryCalendar"]
        self.assertEqual(ordinary["baseYearDays"], 364)
        self.assertEqual(ordinary["weeksPerYear"], 52)
        self.assertEqual(ordinary["day001Weekday"], "Thursday")
        self.assertEqual(
            ordinary["monthLengths"],
            [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 30],
        )
        self.assertEqual(ordinary["quarterDays"], 91)
        self.assertEqual(ordinary["quarters"], 4)
        self.assertFalse(ordinary["hasDecember31"])
        self.assertFalse(ordinary["hasFebruary29"])
        self.assertEqual(
            spec["annualTransition"],
            {"rule": "DAY_364_TO_NEXT_YEAR_DAY_001"},
        )

        serialized = json.dumps(spec)
        self.assertNotIn("LOVELAND_TEST", serialized)
        self.assertNotIn("openingCivilDate", serialized)
        self.assertNotIn("jubileeEpoch", serialized)

    def test_external_witness_artifact_has_zero_grid_authority(self):
        document = build_external_witness_artifact()
        self.assertEqual(
            document["version"],
            EXTERNAL_WITNESS_ARTIFACT_VERSION,
        )
        self.assertEqual(
            document["authorityStatus"],
            "witness-layer-no-grid-authority",
        )
        self.assertFalse(document["jurisdiction"]["gridAuthority"])
        self.assertFalse(document["jurisdiction"]["mayInsertDays"])
        self.assertFalse(document["scope"]["repeatIntoLaterCommonYears"])
        self.assertTrue(document["events"])
        self.assertTrue(
            all(event["calendar_effect"] == "none" for event in document["events"])
        )

    def test_projection_vectors_prove_direct_year_transition(self):
        doc = build_calendar_projection_vectors()
        self.assertEqual(doc["version"], PROJECTION_VECTOR_VERSION)
        self.assertEqual(doc["authorityStatus"], "conformance-only")
        by_id = {row["id"]: row["expected"] for row in doc["vectors"]}

        end = by_id["day-364-december-30"]
        self.assertEqual(end["calendarAddress"], "Y_1-364")
        self.assertEqual(end["commonDate"]["ordinal"], 364)
        self.assertEqual(
            (end["commonDate"]["month"], end["commonDate"]["day"]),
            (12, 30),
        )

        next_year = by_id["next-year-day-001"]
        self.assertEqual(next_year["calendarAddress"], "Y_2-001")
        self.assertEqual(next_year["continuousK"], 364)
        self.assertEqual(next_year["commonDate"]["ordinal"], 1)
        self.assertEqual(
            (next_year["commonDate"]["month"], next_year["commonDate"]["day"]),
            (1, 1),
        )


    def test_publication_rows_are_exactly_364_days_apart(self):
        rows = self._publication()["years"]
        result = validate_publication_rows(rows)
        self.assertEqual(result.first_opening, date(2026, 1, 1))
        self.assertEqual(result.first_year, 1)
        self.assertEqual(result.last_year, 2)
        self.assertEqual(result.year_count, 2)

    def test_publication_rejects_365_day_span(self):
        rows = [
            {"year": 1, "openingCivilDate": "2026-01-01"},
            {"year": 2, "openingCivilDate": "2027-01-01"},
        ]
        with self.assertRaises(PublicationValidationError) as raised:
            validate_publication_rows(rows)
        self.assertEqual(raised.exception.code, "OPENING_SPAN_MISMATCH")

    def test_publication_rejects_unknown_year_row_field(self):
        rows = [
            {
                "year": 1,
                "openingCivilDate": "2026-01-01",
                "unexpectedExtraDateField": 7,
            }
        ]
        with self.assertRaises(PublicationValidationError) as raised:
            validate_publication_rows(rows)
        self.assertEqual(
            raised.exception.code,
            "UNSUPPORTED_PUBLICATION_ROW_FIELD",
        )

    def test_publication_envelope_binds_authority_epoch_and_spec(self):
        envelope = validate_publication_document(
            self._publication(),
            authorized_authority_ids={"PILOT_AUTHORITY"},
            require_authority_status="pilot",
            expected_first_opening=date(2026, 1, 1),
            expected_first_year=1,
            at_opening=date(2026, 12, 31),
        )
        self.assertEqual(envelope.publication_version, PUBLICATION_VERSION)
        self.assertEqual(envelope.calendar_core_spec_version, SPEC_VERSION)
        self.assertEqual(envelope.authority_id, "PILOT_AUTHORITY")
        self.assertEqual(envelope.publication_range.year_count, 2)

    def test_publication_projection_is_translation_only(self):
        document = self._publication()
        semantics = document["projectionSemantics"]
        self.assertEqual(
            semantics["openingCivilDate"]["role"],
            "external-translation-only",
        )
        self.assertFalse(
            semantics["openingCivilDate"]["gridAuthority"]
        )
        self.assertEqual(
            semantics["commonYear"]["opening"],
            {"month": 1, "day": 1},
        )
        self.assertEqual(
            semantics["commonYear"]["closing"],
            {"month": 12, "day": 30},
        )

        document["projectionSemantics"]["openingCivilDate"]["gridAuthority"] = True
        document["publicationDigest"] = publication_digest(document)
        with self.assertRaises(PublicationValidationError) as raised:
            validate_publication_document(document)
        self.assertEqual(
            raised.exception.code,
            "INVALID_PROJECTION_SEMANTICS",
        )

    def test_publication_rejects_tampering(self):
        document = self._publication()
        document["years"][1]["openingCivilDate"] = "2027-01-01"
        with self.assertRaises(PublicationValidationError) as raised:
            validate_publication_document(document)
        self.assertEqual(raised.exception.code, "PUBLICATION_DIGEST_MISMATCH")

    def test_publication_rejects_wrong_spec_with_valid_digest(self):
        document = self._publication()
        document["calendarCoreSpecVersion"] = "future-spec"
        document["publicationDigest"] = publication_digest(document)
        with self.assertRaises(PublicationValidationError) as raised:
            validate_publication_document(document)
        self.assertEqual(
            raised.exception.code,
            "UNSUPPORTED_CALENDAR_SPEC_VERSION",
        )

    def test_publication_rejects_unauthorized_authority(self):
        with self.assertRaises(PublicationValidationError) as raised:
            validate_publication_document(
                self._publication(),
                authorized_authority_ids={"OTHER"},
            )
        self.assertEqual(
            raised.exception.code,
            "UNAUTHORIZED_PUBLICATION_AUTHORITY",
        )

    def test_publication_expires_without_erasing_history(self):
        document = self._publication()
        envelope = validate_publication_document(document)
        with self.assertRaises(PublicationValidationError) as raised:
            validate_publication_document(
                document,
                at_opening=envelope.publication_range.expires_at_opening,
            )
        self.assertEqual(raised.exception.code, "PUBLICATION_EXPIRED")

    def test_superseded_publication_loses_operational_authority(self):
        document = self._publication()
        with self.assertRaises(PublicationValidationError) as raised:
            validate_publication_document(
                document,
                superseded_publication_digests={
                    document["publicationDigest"]
                },
            )
        self.assertEqual(raised.exception.code, "PUBLICATION_SUPERSEDED")


if __name__ == "__main__":
    unittest.main()
