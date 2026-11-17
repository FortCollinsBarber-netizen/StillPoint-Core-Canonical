"""Public-only qualification of StillPoint's author-selected Calendar Core.

No private repo, private artifact, authentication token, or external service is used.
A pass only qualifies the public Calendar Core contract, never private consumers.
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest

from stillpoint.calendar_core.long_cycles import JubileeConfiguration
from stillpoint.calendar_core.runtime_surface import calendar_day_payload
from stillpoint.calendar_core.sacred import (
    common_from_sacred,
    sacred_from_common,
)

SELECTED = "author-selected-working-rule-not-civil-enactment"
AUTHOR = "Robert Emmanuel LaDay"
DATE = "2026-11-17"


class PublicCalendarQualification(unittest.TestCase):
    def test_read_only_public_contract_and_civil_geometry(self):
        for year in (2026, 2027, 2075):
            day = calendar_day_payload(year, 1)
            self.assertEqual(day["schema"], "stillpoint.calendar-day.v2")
            self.assertEqual(day["authority"], "read-only-calendar-law")
            self.assertEqual(day["map"]["first_year"], 2026)
            self.assertEqual(day["map"]["last_year"], 2075)
            self.assertEqual(day["map"]["year_count"], 50)
            self.assertEqual(day["map"]["year_days"], 364)
            self.assertEqual(day["map"]["weeks_per_year"], 52)
            self.assertEqual(day["map"]["total_days"], 18200)
            self.assertFalse(day["map"]["december_31_exists"])
            self.assertFalse(day["common_civil_coordinate"]["daylight_saving_time"])

    def test_selected_sacred_source_anchor_and_provenance(self):
        day = calendar_day_payload(2027, 1)
        profile = day["sacred_year_profile"]
        self.assertEqual(profile["selectionStatus"], SELECTED)
        self.assertEqual(profile["selectedBy"], AUTHOR)
        self.assertEqual(profile["selectedOn"], DATE)
        self.assertEqual((profile["anchorCommonMonth"], profile["anchorCommonDay"]), (3, 25))
        self.assertEqual(profile["anchorWeekday"], "Wednesday")
        self.assertEqual(profile["monthLengths"], [30, 30, 31] * 4)
        self.assertFalse(profile["gridAuthority"])
        self.assertEqual(day["common_civil_coordinate"]["date"], "2027-01-01")
        self.assertEqual((common_from_sacred(2027, 1, 1).month,
                          common_from_sacred(2027, 1, 1).day), (3, 25))
        source = sacred_from_common(2027, 3, 25)
        self.assertEqual((source["year"], source["month"], source["day"]),
                         (2027, 1, 1))

    def test_2027_epoch_overlapping_cycles_and_atonement_scope(self):
        for year, expected in ((2027, 1), (2075, 49)):
            day = calendar_day_payload(year, 1)
            policy = day["long_cycle_policy"]
            self.assertEqual(policy["selectionStatus"], SELECTED)
            self.assertEqual(policy["selectedBy"], AUTHOR)
            self.assertEqual(policy["selectedOn"], DATE)
            self.assertEqual(policy["epochCommonYear"], 2027)
            self.assertEqual(policy["rolloverRule"], "overlap-49")
            self.assertEqual(policy["cycleYears"], 49)
            self.assertTrue(policy["year50OverlapsNextYear1"])
            self.assertFalse(policy["gridAuthority"])
            self.assertEqual(day["jubilee"]["year"], expected)
            self.assertEqual(day["jubilee"]["configuration"]["epoch_common_year"], 2027)
            self.assertEqual(day["jubilee"]["configuration"]["rollover_rule"], "overlap-49")
            self.assertTrue(day["jubilee"]["configuration"]["selected_policy_applies"])

    def test_unpublished_year_and_invalid_ordinal_fail_closed(self):
        for year in (2025, 2076):
            with self.subTest(year=year), self.assertRaises(ValueError):
                calendar_day_payload(year, 1)
        for ordinal in (0, 365):
            with self.subTest(ordinal=ordinal), self.assertRaises(ValueError):
                calendar_day_payload(2075, ordinal)

    def test_nondefault_jubilee_calculation_is_not_operating_authority(self):
        comparison = calendar_day_payload(
            2075, 1,
            jubilee_configuration=JubileeConfiguration(
                epoch_common_year=2026, rollover_rule="standalone-50"
            ),
        )
        cfg = comparison["jubilee"]["configuration"]
        self.assertFalse(cfg["selected_policy_applies"])
        self.assertEqual(cfg["selection_source"], "explicit-call-configuration")
        self.assertEqual(cfg["decision_status"],
                         "explicit-comparison-input-not-author-selected")
        self.assertEqual(comparison["long_cycle_policy"]["rolloverRule"], "overlap-49")
        self.assertEqual(comparison["map"]["last_year"], 2075)

    def test_protected_civic_dusk_is_not_sacred_sunset(self):
        protected = calendar_day_payload(2027, 1)["protected_time"]
        self.assertEqual(protected["sabbath_opens"], "Friday local sunset")
        self.assertEqual(protected["sabbath_closes"], "Saturday local sunset")
        self.assertEqual(protected["stillpoint_opens"],
                         "Friday civil dusk (solar center -6 degrees)")
        self.assertEqual(protected["stillpoint_releases"],
                         "Sunday civil dawn (solar center -6 degrees)")
        self.assertEqual(protected["boundary_authority"],
                         "local-light-overlay-no-grid-mutation")

    def test_public_cli_produces_same_read_only_contract(self):
        process = subprocess.run(
            [sys.executable, "-m", "stillpoint.cli",
             "calendar-day", "2075", "--ordinal", "1"],
            text=True, capture_output=True, check=True, timeout=40,
        )
        payload = json.loads(process.stdout)
        self.assertEqual(payload["calendar_address"], "Y_2075-001")
        self.assertEqual(payload["schema"], "stillpoint.calendar-day.v2")
        self.assertEqual(payload["jubilee"]["year"], 49)
        self.assertEqual(payload["map"]["last_year"], 2075)


if __name__ == "__main__":
    unittest.main()
