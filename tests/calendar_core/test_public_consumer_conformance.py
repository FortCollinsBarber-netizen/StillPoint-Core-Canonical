"""Public-only downstream-consumer conformance at the active Core boundary.

This suite deliberately imports ONLY publicly available Canonical Core modules.
It does not fetch or impersonate RobertOS, StillPointOS, or any private product.
A passing result is Core-interface evidence, not downstream release qualification.
"""

from __future__ import annotations

import unittest

from stillpoint.calendar_core.long_cycles import (
    JubileeConfiguration,
    compare_long_cycles,
)
from stillpoint.calendar_core.runtime_surface import calendar_day_payload


class PublicCoreConsumerConformanceTests(unittest.TestCase):
    def test_consumer_receives_read_only_v2_contract_with_map_boundedness(self):
        value = calendar_day_payload(2026, 1)
        self.assertEqual(value["schema"], "stillpoint.calendar-day.v2")
        self.assertEqual(value["authority"], "read-only-calendar-law")
        self.assertEqual(value["calendar_address"], "Y_2026-001")
        self.assertEqual(
            value["map"],
            {
                "first_year": 2026,
                "last_year": 2075,
                "year_count": 50,
                "total_days": 18200,
                "day001_weekday": "Thursday",
                "year_days": 364,
                "weeks_per_year": 52,
                "december_31_exists": False,
            },
        )
        self.assertEqual(value["publication"]["authority_status"], "enacted")
        self.assertTrue(value["publication"]["digest"])
        self.assertEqual(value["civil_window"]["role"], "external-translation-only")
        self.assertFalse(value["civil_window"]["grid_authority"])

    def test_published_final_day_does_not_infer_next_year_publication(self):
        value = calendar_day_payload(2075, 364)
        self.assertEqual(value["calendar_address"], "Y_2075-364")
        self.assertEqual(value["common_date"]["day"], 30)
        self.assertEqual(value["common_date"]["month"], 12)
        self.assertEqual(value["map"]["last_year"], 2075)
        self.assertEqual(value["jubilee"]["year"], 49)
        self.assertFalse(value["jubilee"]["is_jubilee_year"])

    def test_unpublished_or_invalid_day_fails_closed(self):
        for year, ordinal in ((2025, 1), (2076, 1), (2026, 0), (2026, 365)):
            with self.subTest(year=year, ordinal=ordinal):
                with self.assertRaises(ValueError):
                    calendar_day_payload(year, ordinal)

    def test_author_selected_overlay_is_explicit_and_not_civil_enactment(self):
        value = calendar_day_payload(2027, 1)
        source = value["sacred_year_profile"]
        self.assertEqual(source["selectedBy"], "Robert Emmanuel LaDay")
        self.assertEqual(source["selectedOn"], "2026-11-17")
        self.assertEqual(source["anchorCommonMonth"], 3)
        self.assertEqual(source["anchorCommonDay"], 25)
        self.assertEqual(
            source["selectionStatus"],
            "author-selected-working-rule-not-civil-enactment",
        )
        selected = value["jubilee"]["configuration"]
        self.assertEqual(selected["epoch_common_year"], 2027)
        self.assertEqual(selected["rollover_rule"], "overlap-49")
        self.assertEqual(selected["selection_source"], "declared-project-profile")
        self.assertTrue(selected["selected_policy_applies"])

    def test_explicit_cycle_comparison_does_not_change_published_map(self):
        selected = calendar_day_payload(2075, 1)
        alternate = calendar_day_payload(
            2075,
            1,
            jubilee_configuration=JubileeConfiguration(
                epoch_common_year=2026,
                rollover_rule="standalone-50",
            ),
        )
        for key in (
            "schema", "authority", "calendar_address", "common_date",
            "common_civil_coordinate", "civil_window", "map", "publication",
        ):
            self.assertEqual(selected[key], alternate[key])
        self.assertEqual(
            alternate["jubilee"]["configuration"]["decision_status"],
            "explicit-comparison-input-not-author-selected",
        )
        self.assertFalse(
            alternate["jubilee"]["configuration"]["selected_policy_applies"]
        )
        self.assertEqual(
            alternate["jubilee"]["release_day_projection_status"],
            "computed-under-explicit-comparison-not-author-selected",
        )

    def test_future_jubilee_calculation_is_not_an_issued_calendar_day(self):
        mathematical_only = compare_long_cycles(
            common_year=2076,
            epoch_common_year=2027,
        )
        self.assertEqual(mathematical_only["ordinal_year_from_epoch"], 50)
        self.assertEqual(
            mathematical_only["models"]["consecutive_forty_nine_year_blocks"]["year"],
            1,
        )
        self.assertFalse(mathematical_only["grid_authority"])
        self.assertFalse(mathematical_only["release_authority"])
        with self.assertRaises(ValueError):
            calendar_day_payload(2076, 1)


if __name__ == "__main__":
    unittest.main()
