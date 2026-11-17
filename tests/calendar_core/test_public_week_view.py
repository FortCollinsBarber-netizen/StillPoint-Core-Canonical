"""Public-only executable checks for the read-only Common week view."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from stillpoint.calendar_core.runtime_surface import calendar_day_payload
from stillpoint.calendar_core.week_view import calendar_week_payload
from stillpoint.cli import main


class PublicCalendarWeekTests(unittest.TestCase):
    def test_first_week_has_seven_contiguous_common_dates(self):
        result = calendar_week_payload(2026, 1)
        self.assertEqual(result["schema"], "stillpoint.calendar-week.v1")
        self.assertEqual(result["authority"], "read-only-calendar-law")
        self.assertEqual(result["day_count"], 7)
        self.assertEqual(result["first_address"], "Y_2026-001")
        self.assertEqual(result["last_address"], "Y_2026-007")
        self.assertEqual(
            [d["common_date"]["ordinal"] for d in result["days"]],
            list(range(1, 8)),
        )
        self.assertEqual(result["days"][0]["common_date"]["weekday"], "Thursday")
        self.assertEqual(result["days"][6]["common_date"]["weekday"], "Wednesday")

    def test_week_from_middle_of_year_crosses_month_not_calendar_authority(self):
        week = 5  # Ordinals 29..35 straddle January and February.
        result = calendar_week_payload(2026, week)
        self.assertEqual(result["days"][0]["common_date"]["month"], 1)
        self.assertEqual(result["days"][-1]["common_date"]["month"], 2)
        self.assertTrue(all(d["common_date"]["week"] == week for d in result["days"]))
        for day in result["days"]:
            self.assertFalse(day["civil_window"]["grid_authority"])
            self.assertEqual(
                day["civil_window"]["role"], "external-translation-only"
            )

    def test_final_published_week_is_bounded_by_year_2075_day_364(self):
        result = calendar_week_payload(2075, 52)
        self.assertEqual(result["first_address"], "Y_2075-358")
        self.assertEqual(result["last_address"], "Y_2075-364")
        self.assertEqual(result["map"]["last_year"], 2075)
        self.assertEqual(result["map"]["weeks_per_year"], 52)
        self.assertEqual(result["days"][-1]["common_date"]["month"], 12)
        self.assertEqual(result["days"][-1]["common_date"]["day"], 30)

    def test_each_entry_matches_actual_published_core_day(self):
        result = calendar_week_payload(2027, 13)
        self.assertEqual(result["publication"]["authority_status"], "enacted")
        for day in result["days"]:
            ordinal = day["common_date"]["ordinal"]
            actual = calendar_day_payload(2027, ordinal)
            self.assertEqual(day["calendar_address"], actual["calendar_address"])
            self.assertEqual(day["common_date"], actual["common_date"])
            self.assertEqual(day["civil_window"], actual["civil_window"])
            self.assertEqual(day["sacred_date"], actual["sacred_date"])
            self.assertEqual(
                day["is_sabbath_date"],
                actual["protected_time"]["is_sabbath_date"],
            )

    def test_refuses_unpublished_years(self):
        for year in (2025, 2076, 2125):
            with self.subTest(year=year), self.assertRaises(ValueError):
                calendar_week_payload(year, 1)

    def test_refuses_invalid_week_indices_and_input_types(self):
        for week in (0, 53, -1, True, False, 1.5, "1", None):
            with self.subTest(week=week), self.assertRaises(ValueError):
                calendar_week_payload(2026, week)
        for year in (True, False, 2026.0, "2026", None):
            with self.subTest(year=year), self.assertRaises(ValueError):
                calendar_week_payload(year, 1)

    def test_cli_emits_read_only_json_without_company_database(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            stream = StringIO()
            with patch.dict(os.environ, {"STILLPOINT_ROOT": td}, clear=False):
                with redirect_stdout(stream):
                    result = main(["calendar-week", "2026", "--week", "1"])
            self.assertEqual(result, 0)
            payload = json.loads(stream.getvalue())
            self.assertEqual(payload["schema"], "stillpoint.calendar-week.v1")
            self.assertEqual(len(payload["days"]), 7)
            self.assertFalse((root / "state").exists())

    def test_cli_does_not_issue_week_for_unpublished_year(self):
        with tempfile.TemporaryDirectory() as td:
            stream = StringIO()
            with patch.dict(os.environ, {"STILLPOINT_ROOT": td}, clear=False):
                with redirect_stdout(stream), self.assertRaises(ValueError):
                    main(["calendar-week", "2076", "--week", "1"])
            self.assertEqual(stream.getvalue(), "")
            self.assertFalse((Path(td) / "state").exists())


if __name__ == "__main__":
    unittest.main()
