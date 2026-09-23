import unittest
from datetime import date, timedelta

from stillpoint.calendar_core.population import (
    address,
    iter_fifty_year_map,
)
from stillpoint.calendar_core.population_artifact import (
    POPULATION_ARTIFACT_VERSION,
    build_calendar_population_artifact,
)
from stillpoint.calendar_core.publication import (
    build_projection_semantics,
    PUBLICATION_VERSION,
    publication_digest,
)
from stillpoint.calendar_core.spec import SPEC_VERSION


def fifty_year_publication():
    first = date(2026, 1, 1)
    document = {
        "publicationVersion": PUBLICATION_VERSION,
        "calendarCoreSpecVersion": SPEC_VERSION,
        "authority": {
            "id": "TEST_ENACTED",
            "status": "enacted",
        },
        "projectionSemantics": build_projection_semantics(),
        "years": [
            {
                "year": 2026 + offset,
                "openingCivilDate": (
                    first + timedelta(days=364 * offset)
                ).isoformat(),
            }
            for offset in range(50)
        ],
    }
    document["publicationDigest"] = publication_digest(document)
    return document


class CalendarPopulationTests(unittest.TestCase):
    def setUp(self):
        self.publication = fifty_year_publication()

    def test_population_artifact_has_no_grid_authority(self):
        artifact = build_calendar_population_artifact()
        self.assertEqual(
            artifact["version"],
            POPULATION_ARTIFACT_VERSION,
        )
        self.assertEqual(
            artifact["authorityStatus"],
            "population-layer-no-grid-authority",
        )
        self.assertFalse(
            artifact["jurisdiction"]["gridAuthority"]
        )
        self.assertFalse(
            artifact["jurisdiction"]["mayInsertDays"]
        )
        self.assertEqual(
            sum(
                artifact["seasonalArchitecture"][
                    "phaseLengths"
                ]
            ),
            364,
        )

    def test_full_map_has_exactly_18200_unique_addresses(self):
        rows = list(
            iter_fifty_year_map(
                publication_document=self.publication,
                jubilee_epoch_common_year=2026,
            )
        )
        self.assertEqual(len(rows), 18_200)
        self.assertEqual(
            len({row.calendar_address for row in rows}),
            18_200,
        )
        self.assertEqual(rows[0].calendar_address, "Y_2026-001")
        self.assertEqual(rows[-1].calendar_address, "Y_2075-364")

    def test_december_30_is_last_day_and_next_year_opens_next_civil_day(self):
        last = address(
            publication_document=self.publication,
            year=2026,
            month=12,
            day=30,
        )
        nxt = address(
            publication_document=self.publication,
            year=2027,
            month=1,
            day=1,
        )
        self.assertEqual(last.ordinal, 364)
        self.assertEqual(last.weekday, "Wednesday")
        self.assertEqual(nxt.ordinal, 1)
        self.assertEqual(nxt.weekday, "Thursday")
        self.assertEqual(
            nxt.opening_civil_date - last.opening_civil_date,
            timedelta(days=1),
        )

        with self.assertRaises(ValueError):
            address(
                publication_document=self.publication,
                year=2026,
                month=12,
                day=31,
            )

    def test_firstfruits_and_weeks_land_on_sunday(self):
        firstfruits = address(
            publication_document=self.publication,
            year=2026,
            month=1,
            day=25,
        )
        weeks = address(
            publication_document=self.publication,
            year=2026,
            month=3,
            day=15,
        )
        self.assertEqual(firstfruits.weekday, "Sunday")
        self.assertEqual(weeks.weekday, "Sunday")
        self.assertIn("Firstfruits", firstfruits.observance_names)
        self.assertIn(
            "Feast of Weeks / Pentecost",
            weeks.observance_names,
        )
        self.assertIn(
            "Leviticus 23:15-21",
            weeks.source_refs,
        )

    def test_fixed_civic_observances_retain_weekdays(self):
        for year in (2026, 2036, 2056, 2075):
            thanksgiving = address(
                publication_document=self.publication,
                year=year,
                month=11,
                day=26,
            )
            christmas = address(
                publication_document=self.publication,
                year=year,
                month=12,
                day=25,
            )
            mothers = address(
                publication_document=self.publication,
                year=year,
                month=5,
                day=10,
            )
            fathers = address(
                publication_document=self.publication,
                year=year,
                month=6,
                day=21,
            )
            self.assertEqual(thanksgiving.weekday, "Thursday")
            self.assertEqual(christmas.weekday, "Friday")
            self.assertEqual(mothers.weekday, "Sunday")
            self.assertEqual(fathers.weekday, "Sunday")

    def test_enochic_phase_gate_and_source_remain_witness_metadata(self):
        row = address(
            publication_document=self.publication,
            year=2026,
            month=10,
            day=1,
        )
        self.assertTrue(1 <= row.enoch_phase <= 12)
        self.assertTrue(1 <= row.enoch_gate <= 6)
        self.assertIn("1 Enoch 72-82", row.source_refs)
        self.assertIn("Jubilees 6:29-32", row.source_refs)

    def test_sabbath_source_provenance_attaches_to_saturday_dates(self):
        saturday = address(
            publication_document=self.publication,
            year=2026,
            month=1,
            day=3,
        )
        self.assertEqual(saturday.weekday, "Saturday")
        self.assertTrue(saturday.is_sabbath_date)
        self.assertIn("Leviticus 23:3", saturday.source_refs)

    def test_jubilee_cycle_is_layered_without_changing_addresses(self):
        thresholds = []
        for year in range(2026, 2075):
            row = address(
                publication_document=self.publication,
                year=year,
                month=1,
                day=1,
                jubilee_epoch_common_year=2026,
            )
            if row.is_sabbatical_threshold:
                thresholds.append(row.jubilee_year)

        self.assertEqual(
            thresholds,
            [7, 14, 21, 28, 35, 42, 49],
        )

        year50 = address(
            publication_document=self.publication,
            year=2075,
            month=1,
            day=1,
            jubilee_epoch_common_year=2026,
        )
        release = address(
            publication_document=self.publication,
            year=2075,
            month=7,
            day=10,
            jubilee_epoch_common_year=2026,
        )
        self.assertEqual(year50.jubilee_year, 50)
        self.assertTrue(year50.is_jubilee_year)
        self.assertTrue(release.is_jubilee_release_day)
        self.assertIn("Leviticus 25:8-13", release.source_refs)


if __name__ == "__main__":
    unittest.main()
