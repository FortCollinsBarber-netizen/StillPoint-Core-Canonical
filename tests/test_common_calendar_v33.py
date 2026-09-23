import datetime as dt
import unittest

from tools import generate_common_calendar_v33 as v33


class FixedCommonCalendarGeneratorTests(unittest.TestCase):
    latitude = 40.3978
    longitude = -105.0749
    custody_nonce = "x" * 64

    def _generate(self, *, count=50, ephemerides=None):
        return v33.generate(
            latitude=self.latitude,
            longitude=self.longitude,
            first_year_label=2026,
            first_opening=dt.date(2026, 1, 1),
            count=count,
            ephemerides=ephemerides or {},
            ephemeris_source="TEST_WITNESS",
            ephemeris_sha256="a" * 64,
            coordinate_custody_nonce=self.custody_nonce,
            publish_coordinates=False,
            authority_id="TEST_AUTHORITY",
            authority_status="pilot",
            reference_point_id="PUBLIC_TEST_POINT",
        )

    def test_fifty_year_publication_is_exactly_364_days_per_year(self):
        doc = self._generate()
        self.assertEqual(len(doc["years"]), 50)
        self.assertEqual(
            doc["referenceRuleVersion"],
            "fixed-364-v1",
        )
        self.assertEqual(
            doc["gridRule"]["yearDays"],
            364,
        )
        self.assertEqual(
            doc["gridRule"]["reconciliationDays"],
            0,
        )

        for index, row in enumerate(doc["years"]):
            self.assertEqual(
                row["year"],
                2026 + index,
            )
            self.assertEqual(
                row["reconciliationDaysAfterCompletion"],
                0,
            )
            expected = (
                dt.date(2026, 1, 1)
                + dt.timedelta(days=364 * index)
            )
            self.assertEqual(
                row["openingCivilDate"],
                expected.isoformat(),
            )

        self.assertEqual(
            doc["years"][1]["openingCivilDate"],
            "2026-12-31",
        )
        self.assertEqual(
            doc["years"][49]["openingCivilDate"],
            "2074-11-01",
        )
        v33.validate_output(doc)

    def test_astronomy_is_witness_only_and_cannot_move_openings(self):
        a = self._generate(
            count=3,
            ephemerides={},
        )
        b = self._generate(
            count=3,
            ephemerides={
                2027: dt.datetime(
                    2027,
                    3,
                    20,
                    12,
                    tzinfo=dt.timezone.utc,
                )
            },
        )
        self.assertEqual(
            a["years"],
            b["years"],
        )

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
        doc = self._generate(count=2)
        v33.validate_output(doc)
        doc["years"][0]["year"] = 9999
        with self.assertRaisesRegex(
            ValueError,
            "publication digest mismatch",
        ):
            v33.validate_output(doc)

    def test_reference_point_id_is_not_structurally_hardcoded(self):
        doc = self._generate(count=1)
        self.assertEqual(
            doc["referencePoint"]["id"],
            "PUBLIC_TEST_POINT",
        )
        v33.validate_output(doc)

    def test_reconciliation_cannot_be_reintroduced(self):
        doc = self._generate(count=1)
        doc["years"][0][
            "reconciliationDaysAfterCompletion"
        ] = 7
        doc["publicationDigest"] = v33.publication_digest(
            doc
        )
        with self.assertRaisesRegex(
            ValueError,
            "reconciliation is prohibited",
        ):
            v33.validate_output(doc)

    def test_count_must_be_positive(self):
        with self.assertRaises(ValueError):
            self._generate(count=0)


if __name__ == "__main__":
    unittest.main()
