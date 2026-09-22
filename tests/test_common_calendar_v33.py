import datetime as dt
import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "generate_common_calendar_v33.py"
SPEC = importlib.util.spec_from_file_location("common_calendar_v33", MODULE_PATH)
assert SPEC and SPEC.loader
v33 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v33)


class CommonCalendarV33Tests(unittest.TestCase):
    latitude = 40.4
    longitude = -105.1
    custody_nonce = "test-private-custody-nonce-" + ("x" * 40)

    def test_fixed_spring_gate_is_common_march_20_ordinal_80(self):
        self.assertEqual(v33.SPRING_GATE_ORDINAL, 80)
        opening = dt.date(2026, 12, 31)
        self.assertEqual(
            v33.spring_gate_date(opening),
            dt.date(2027, 3, 20),
        )

    def test_governing_equinox_year_comes_from_candidate_geometry_not_year_label(self):
        opening = dt.date(2026, 1, 1)
        self.assertEqual(
            v33.governing_equinox_year(opening),
            2027,
        )

        doc = v33.generate(
            latitude=self.latitude,
            longitude=self.longitude,
            first_year_label=1,
            first_opening=opening,
            count=1,
            ephemerides={
                2027: v33.sunset_utc(
                    v33.spring_gate_date(
                        opening + dt.timedelta(days=364)
                    ),
                    self.latitude,
                    self.longitude,
                )
            },
            ephemeris_source="test",
            ephemeris_sha256="0" * 64,
            coordinate_custody_nonce=self.custody_nonce,
            publish_coordinates=False,
        )
        self.assertEqual(doc["years"][0]["year"], 1)
        self.assertEqual(
            doc["years"][0]["governingMarchEquinoxYear"],
            2027,
        )

    def test_immediate_reentry_wins_when_its_spring_gate_matches_equinox(self):
        opening = dt.date(2026, 1, 1)
        immediate_next = opening + dt.timedelta(days=364)
        immediate_gate = v33.spring_gate_date(immediate_next)
        equinox = v33.sunset_utc(
            immediate_gate,
            self.latitude,
            self.longitude,
        )

        doc = v33.generate(
            latitude=self.latitude,
            longitude=self.longitude,
            first_year_label=2026,
            first_opening=opening,
            count=1,
            ephemerides={2027: equinox},
            ephemeris_source="test",
            ephemeris_sha256="0" * 64,
            coordinate_custody_nonce=self.custody_nonce,
            publish_coordinates=False,
        )

        row = doc["years"][0]
        self.assertEqual(
            row["reconciliationDaysAfterCompletion"],
            0,
        )
        self.assertEqual(
            row["reconciliationReasonCode"],
            "IMMEDIATE_CLOSER_OR_TIE",
        )
        self.assertEqual(
            row["immediateCandidateOpeningCivilDate"],
            "2026-12-31",
        )
        self.assertEqual(
            row["nextYearSpringGateCivilDate"],
            "2027-03-20",
        )
        self.assertEqual(
            doc["snapOperator"],
            "NearestLegalSpringGate",
        )
        self.assertEqual(
            doc["seasonalAnchor"]["ordinal"],
            80,
        )
        self.assertEqual(
            doc["publicationVersion"],
            v33.PUBLICATION_VERSION,
        )
        self.assertEqual(
            doc["calendarCoreSpecVersion"],
            v33.SPEC_VERSION,
        )
        self.assertEqual(
            doc["authority"]["status"],
            "pilot",
        )
        self.assertEqual(
            doc["referenceRuleVersion"],
            "v3.3-candidate",
        )
        v33.validate_output(doc)

    def test_delayed_reentry_is_separate_week_not_371_day_year(self):
        opening = dt.date(2026, 1, 1)
        delayed_next = opening + dt.timedelta(days=371)
        delayed_gate = v33.spring_gate_date(delayed_next)
        equinox = v33.sunset_utc(
            delayed_gate,
            self.latitude,
            self.longitude,
        )

        doc = v33.generate(
            latitude=self.latitude,
            longitude=self.longitude,
            first_year_label=2026,
            first_opening=opening,
            count=1,
            ephemerides={2027: equinox},
            ephemeris_source="test",
            ephemeris_sha256="1" * 64,
            coordinate_custody_nonce=self.custody_nonce,
            publish_coordinates=False,
        )

        row = doc["years"][0]
        self.assertEqual(
            row["reconciliationDaysAfterCompletion"],
            7,
        )
        self.assertEqual(
            row["reconciliationReasonCode"],
            "RECONCILIATION_WEEK_CLOSER",
        )
        self.assertNotIn("yearLength", row)
        self.assertEqual(
            (
                dt.date.fromisoformat(
                    row["delayedCandidateOpeningCivilDate"]
                )
                - dt.date.fromisoformat(
                    row["immediateCandidateOpeningCivilDate"]
                )
            ).days,
            7,
        )
        v33.validate_output(doc)

    def test_coordinate_commitment_is_nonce_protected(self):
        a = v33.coordinate_custody_digest(
            self.latitude,
            self.longitude,
            self.custody_nonce,
        )
        b = v33.coordinate_custody_digest(
            self.latitude,
            self.longitude,
            self.custody_nonce + "different",
        )
        self.assertNotEqual(a, b)

    def test_publication_digest_detects_tampering(self):
        opening = dt.date(2026, 1, 1)
        gate = v33.spring_gate_date(
            opening + dt.timedelta(days=364)
        )
        doc = v33.generate(
            latitude=self.latitude,
            longitude=self.longitude,
            first_year_label=2026,
            first_opening=opening,
            count=1,
            ephemerides={
                2027: v33.sunset_utc(
                    gate,
                    self.latitude,
                    self.longitude,
                )
            },
            ephemeris_source="test",
            ephemeris_sha256="f" * 64,
            coordinate_custody_nonce=self.custody_nonce,
            publish_coordinates=False,
        )
        v33.validate_output(doc)
        doc["years"][0]["year"] = 9999
        with self.assertRaisesRegex(
            ValueError,
            "publication digest mismatch",
        ):
            v33.validate_output(doc)

    def test_missing_governing_equinox_fails_closed(self):
        with self.assertRaises(v33.AstronomyEvidenceError) as raised:
            v33.generate(
                latitude=self.latitude,
                longitude=self.longitude,
                first_year_label=1,
                first_opening=dt.date(2026, 1, 1),
                count=1,
                ephemerides={},
                ephemeris_source="test",
                ephemeris_sha256="0" * 64,
                coordinate_custody_nonce=self.custody_nonce,
                publish_coordinates=False,
            )
        self.assertEqual(
            raised.exception.code,
            "MISSING_ASTRONOMY_EVIDENCE",
        )

    def test_two_openings_obey_declared_transition(self):
        opening = dt.date(2026, 1, 1)
        next1 = opening + dt.timedelta(days=364)
        next2 = next1 + dt.timedelta(days=364)

        doc = v33.generate(
            latitude=self.latitude,
            longitude=self.longitude,
            first_year_label=2026,
            first_opening=opening,
            count=2,
            ephemerides={
                2027: v33.sunset_utc(
                    v33.spring_gate_date(next1),
                    self.latitude,
                    self.longitude,
                ),
                2028: v33.sunset_utc(
                    v33.spring_gate_date(next2),
                    self.latitude,
                    self.longitude,
                ),
            },
            ephemeris_source="test",
            ephemeris_sha256="2" * 64,
            coordinate_custody_nonce=self.custody_nonce,
            publish_coordinates=False,
        )

        first = dt.date.fromisoformat(
            doc["years"][0]["openingCivilDate"]
        )
        second = dt.date.fromisoformat(
            doc["years"][1]["openingCivilDate"]
        )
        self.assertEqual(
            (second - first).days,
            364,
        )
        v33.validate_output(doc)

    def test_reference_point_id_is_not_structurally_hardcoded_to_ground_zero(self):
        opening = dt.date(2026, 1, 1)
        next1 = opening + dt.timedelta(days=364)
        doc = v33.generate(
            latitude=self.latitude,
            longitude=self.longitude,
            first_year_label=2026,
            first_opening=opening,
            count=1,
            ephemerides={
                2027: v33.sunset_utc(
                    v33.spring_gate_date(next1),
                    self.latitude,
                    self.longitude,
                )
            },
            ephemeris_source="test",
            ephemeris_sha256="3" * 64,
            coordinate_custody_nonce=self.custody_nonce,
            publish_coordinates=False,
            reference_point_id="PUBLIC_TEST_POINT",
        )
        self.assertEqual(
            doc["referencePoint"]["id"],
            "PUBLIC_TEST_POINT",
        )
        v33.validate_output(doc)


if __name__ == "__main__":
    unittest.main()
