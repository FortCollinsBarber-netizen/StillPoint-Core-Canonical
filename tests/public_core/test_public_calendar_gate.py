"""Operator-facing public-only tests absent from the existing consumer suite.

No private repository, credential, manuscript, or hidden integration fixture is used.
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest

from stillpoint.calendar_core.runtime_surface import calendar_day_payload


class PublicOperatorQualification(unittest.TestCase):
    def test_installed_public_cli_returns_v2_and_bounded_final_year(self):
        process = subprocess.run(
            [sys.executable, "-m", "stillpoint.cli",
             "calendar-day", "2075", "--ordinal", "1"],
            capture_output=True, text=True, check=True, timeout=40,
        )
        result = json.loads(process.stdout)
        self.assertEqual(result["schema"], "stillpoint.calendar-day.v2")
        self.assertEqual(result["authority"], "read-only-calendar-law")
        self.assertEqual(result["calendar_address"], "Y_2075-001")
        self.assertEqual(result["jubilee"]["year"], 49)
        self.assertEqual(result["map"]["last_year"], 2075)

    def test_public_cli_refuses_unpublished_next_year(self):
        result = subprocess.run(
            [sys.executable, "-m", "stillpoint.cli",
             "calendar-day", "2076", "--ordinal", "1"],
            capture_output=True, text=True, timeout=40,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_public_consumer_does_not_conflate_civic_and_sacred_boundaries(self):
        protected = calendar_day_payload(2027, 1)["protected_time"]
        self.assertEqual(protected["sabbath_opens"], "Friday local sunset")
        self.assertEqual(protected["sabbath_closes"], "Saturday local sunset")
        self.assertEqual(protected["stillpoint_opens"],
                         "Friday civil dusk (solar center -6 degrees)")
        self.assertEqual(protected["stillpoint_releases"],
                         "Sunday civil dawn (solar center -6 degrees)")
        self.assertEqual(protected["boundary_authority"],
                         "local-light-overlay-no-grid-mutation")


if __name__ == "__main__":
    unittest.main()
