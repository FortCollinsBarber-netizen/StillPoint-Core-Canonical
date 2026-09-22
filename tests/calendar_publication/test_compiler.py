import copy
import json
import unittest
from datetime import date, timedelta
from pathlib import Path

from stillpoint.calendar_core.models import GeoPoint
from stillpoint.calendar_core.sunset import apparent_sunset_utc
from stillpoint.calendar_publication import (
    compile_v33_publication,
    publication_digest,
    spring_gate_date,
    validate_calendar_publication,
)


class CalendarPublicationTests(unittest.TestCase):
    point = GeoPoint(40.4, -105.1, "REFERENCE_TEST")

    def evidence(self):
        opening_2026 = date(2026, 1, 1)
        opening_2027 = opening_2026 + timedelta(days=364)
        opening_2028 = opening_2027 + timedelta(days=364)
        return {
            2027: apparent_sunset_utc(spring_gate_date(opening_2027), self.point),
            2028: apparent_sunset_utc(spring_gate_date(opening_2028), self.point),
        }

    def compile(self, **overrides):
        kwargs = dict(
            publication_id="CONFORMANCE-2026-2Y",
            authority_status="CONFORMANCE",
            authority_id="TEST_ONLY",
            reference_point=self.point,
            reference_point_id=self.point.id,
            reference_geometry_digest="a" * 64,
            first_year_label=2026,
            first_opening=date(2026, 1, 1),
            first_opening_continuous_k=0,
            day001_weekday="Friday",
            count=2,
            march_equinoxes=self.evidence(),
            evidence_source_id="TEST_EPHEMERIS",
            evidence_digest="b" * 64,
        )
        kwargs.update(overrides)
        return compile_v33_publication(**kwargs)

    def test_publication_is_finite_and_keeps_ordinary_year_364(self):
        doc = self.compile()
        self.assertEqual(doc["authority"]["status"], "CONFORMANCE")
        self.assertEqual(doc["effectiveRange"]["yearCount"], 2)
        self.assertEqual(len(doc["years"]), 2)
        for row in doc["years"]:
            self.assertEqual(row["ordinaryDays"], 364)
            self.assertIn(row["reconciliationDaysAfterCompletion"], (0, 7))
            self.assertEqual(
                row["nextOpeningContinuousK"] - row["openingContinuousK"],
                364 + row["reconciliationDaysAfterCompletion"],
            )

    def test_checked_in_publication_is_only_a_conformance_fixture(self):
        root = Path(__file__).resolve().parents[2]
        fixture = json.loads(
            (
                root / "tests/fixtures/calendar/calendar_publication.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(fixture["authority"]["status"], "CONFORMANCE")
        self.assertEqual(fixture["authority"]["authorityId"], "TEST_ONLY")
        validate_calendar_publication(fixture)

    def test_evidence_cannot_compile_without_explicit_authority(self):
        with self.assertRaises(ValueError):
            self.compile(authority_status="")

    def test_missing_evidence_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "EPHEMERIS_UNAVAILABLE"):
            self.compile(march_equinoxes={})

    def test_illegal_reconciliation_cannot_survive_validation(self):
        doc = self.compile()
        tampered = copy.deepcopy(doc)
        tampered["years"][0]["reconciliationDaysAfterCompletion"] = 1
        tampered["publicationDigest"] = publication_digest(tampered)
        with self.assertRaisesRegex(ValueError, "reconciliation"):
            validate_calendar_publication(tampered)


if __name__ == "__main__":
    unittest.main()
