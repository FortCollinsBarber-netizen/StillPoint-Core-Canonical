"""Public-only tests for civil-date lookup against the finite Common publication."""
from __future__ import annotations

from datetime import date, datetime, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from stillpoint.calendar_core.civil_lookup import civil_date_lookup_payload
from stillpoint.calendar_core.runtime_surface import (
    calendar_day_payload,
    load_enacted_publication,
)


class PublicCivilDateLookupTests(unittest.TestCase):
    def test_first_day_and_first_year_boundary_translate_without_changing_law(self):
        first = civil_date_lookup_payload("2026-01-01")
        self.assertEqual(first["schema"], "stillpoint.civil-date-lookup.v1")
        self.assertEqual(first["calendar_day"]["calendar_address"], "Y_2026-001")
        self.assertEqual(first["calendar_day"], calendar_day_payload(2026, 1))
        self.assertFalse(first["translation"]["grid_authority"])
        self.assertEqual(first["translation"]["role"], "external-translation-only")

        last = civil_date_lookup_payload(date(2026, 12, 30))
        self.assertEqual(last["calendar_day"]["calendar_address"], "Y_2026-364")
        next_year = civil_date_lookup_payload("2026-12-31")
        self.assertEqual(next_year["calendar_day"]["calendar_address"], "Y_2027-001")
        self.assertEqual(next_year["calendar_day"]["common_date"]["year"], 2027)
        self.assertEqual(next_year["civil_date"], "2026-12-31")

    def test_gregorian_leap_day_maps_using_published_day_openings(self):
        result = civil_date_lookup_payload("2028-02-29")
        day = result["calendar_day"]
        self.assertEqual(day["civil_window"]["opens"], "2028-02-29")
        self.assertEqual(day["civil_window"]["role"], "external-translation-only")
        self.assertEqual(day["common_date"]["ordinal"], int(day["calendar_address"][-3:]))
        self.assertEqual(day, calendar_day_payload(
            day["common_date"]["year"], day["common_date"]["ordinal"]
        ))

    def test_last_published_day_is_valid_but_next_day_fails_closed(self):
        document = load_enacted_publication()
        last_year = document["years"][-1]["year"]
        self.assertEqual(last_year, 2075)
        last_date = date.fromisoformat(document["years"][-1]["openingCivilDate"]) + timedelta(days=363)
        result = civil_date_lookup_payload(last_date.isoformat())
        self.assertEqual(result["calendar_day"]["calendar_address"], "Y_2075-364")
        with self.assertRaises(ValueError):
            civil_date_lookup_payload(last_date + timedelta(days=1))

    def test_invalid_and_unpublished_dates_are_rejected(self):
        for value in ("2025-12-31", "2026-2-03", "2026-02-29",
                      "2076-01-01", "not-a-date", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                civil_date_lookup_payload(value)
        with self.assertRaises(ValueError):
            civil_date_lookup_payload(datetime(2026, 11, 17, 10, 0))

    def test_external_consumer_needs_no_keys_or_company_state(self):
        with tempfile.TemporaryDirectory(prefix="stillpoint-date-test-") as directory:
            root = Path(directory)
            env = os.environ.copy()
            env["STILLPOINT_ROOT"] = str(root)
            env["STILLPOINT_PROVIDER"] = "mock"
            for key in ("OPENAI_API_KEY", "XAI_API_KEY", "ANTHROPIC_API_KEY"):
                env.pop(key, None)
            result = subprocess.run(
                [sys.executable, "-m", "stillpoint.calendar_core.civil_lookup",
                 "2026-11-17"],
                cwd=root, env=env, capture_output=True, text=True,
                check=False, timeout=45,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["civil_date"], "2026-11-17")
            self.assertEqual(payload["calendar_day"]["civil_window"]["opens"], "2026-11-17")
            self.assertEqual(list(root.iterdir()), [], "lookup must not write state")

            bad = subprocess.run(
                [sys.executable, "-m", "stillpoint.calendar_core.civil_lookup",
                 "2076-01-01"],
                cwd=root, env=env, capture_output=True, text=True,
                check=False, timeout=45,
            )
            self.assertNotEqual(bad.returncode, 0)
            self.assertFalse(bad.stdout.strip(), "unpublished date must not emit JSON")
            self.assertEqual(list(root.iterdir()), [], "rejected lookup must not write state")


if __name__ == "__main__":
    unittest.main()
