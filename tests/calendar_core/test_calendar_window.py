"""Real Calendar Core calendar-window capability and operator boundary tests."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from stillpoint.calendar_core.runtime_surface import (
    WINDOW_SCHEMA,
    calendar_day_payload,
    calendar_window_payload,
)
from stillpoint.cli import main


class CalendarWindowTests(unittest.TestCase):
    def test_seven_day_window_reuses_existing_day_contract(self):
        value = calendar_window_payload(2026, 1)
        self.assertEqual(value["schema"], WINDOW_SCHEMA)
        self.assertEqual(value["authority"], "read-only-calendar-law")
        self.assertEqual(value["calendar_day_schema"], "stillpoint.calendar-day.v2")
        self.assertEqual(value["request"], {
            "year": 2026, "start_ordinal": 1, "days": 7, "end_ordinal": 7,
        })
        self.assertEqual(value["bounds"]["first_address"], "Y_2026-001")
        self.assertEqual(value["bounds"]["last_address"], "Y_2026-007")
        self.assertTrue(value["bounds"]["within_one_published_common_year"])
        self.assertEqual(value["map"]["year_days"], 364)
        self.assertEqual(value["publication"]["authority_status"], "enacted")
        self.assertFalse(value["civil_or_legal_execution_authorized"])
        self.assertEqual(len(value["days"]), 7)
        for index, day in enumerate(value["days"], 1):
            self.assertEqual(day, calendar_day_payload(2026, index))

    def test_sacred_year_boundary_is_visible_without_mutating_common_dates(self):
        value = calendar_window_payload(2027, 83, 3)
        self.assertEqual(
            [day["common_civil_coordinate"]["date"] for day in value["days"]],
            ["2027-03-24", "2027-03-25", "2027-03-26"],
        )
        before, anchor, after = [d["sacred_date"] for d in value["days"]]
        self.assertEqual((before["year"], before["month"], before["day"]),
                         (2026, 12, 31))
        self.assertEqual((anchor["year"], anchor["month"], anchor["day"]),
                         (2027, 1, 1))
        self.assertEqual((after["year"], after["month"], after["day"]),
                         (2027, 1, 2))
        self.assertEqual(value["sacred_year_profile"]["selectionStatus"],
                         "author-selected-working-rule-not-civil-enactment")
        self.assertEqual(value["long_cycle_policy"]["epochCommonYear"], 2027)
        self.assertEqual(value["long_cycle_policy"]["rolloverRule"], "overlap-49")

    def test_last_published_day_is_valid_without_implicit_next_year(self):
        last = calendar_window_payload(2075, 364, 1)
        self.assertEqual(last["bounds"]["last_address"], "Y_2075-364")
        self.assertEqual(last["days"][0]["jubilee"]["year"], 49)
        self.assertEqual(last["map"]["last_year"], 2075)
        with self.assertRaises(ValueError):
            calendar_window_payload(2075, 364, 2)
        with self.assertRaises(ValueError):
            calendar_window_payload(2076, 1, 1)

    def test_31_day_bound_and_input_validation(self):
        self.assertEqual(len(calendar_window_payload(2026, 1, 31)["days"]), 31)
        for bad in (0, -1, 32, True, 1.5, "7"):
            with self.subTest(days=bad), self.assertRaises(ValueError):
                calendar_window_payload(2026, 1, bad)
        for bad in (0, 365, True, "1"):
            with self.subTest(ordinal=bad), self.assertRaises(ValueError):
                calendar_window_payload(2026, bad, 1)
        for bad in (True, 2026.0, "2026"):
            with self.subTest(year=bad), self.assertRaises(ValueError):
                calendar_window_payload(bad, 1, 1)

    def test_crossing_any_year_boundary_is_rejected_before_partial_output(self):
        for start, count in ((358, 8), (364, 2), (365, 1)):
            with self.subTest(start=start, count=count), self.assertRaises(ValueError):
                calendar_window_payload(2026, start, count)
        # A complete last week remains within the one-year coordinate.
        valid = calendar_window_payload(2026, 358, 7)
        self.assertEqual(valid["bounds"]["last_address"], "Y_2026-364")

    def test_cli_is_read_only_and_does_not_create_company_state(self):
        with tempfile.TemporaryDirectory() as td:
            stream = StringIO()
            with patch.dict(os.environ, {"STILLPOINT_ROOT": td}, clear=False):
                with redirect_stdout(stream):
                    rc = main(["calendar-window", "2027",
                               "--start-ordinal", "83", "--days", "3"])
            self.assertEqual(rc, 0)
            response = json.loads(stream.getvalue())
            self.assertEqual(response["schema"], WINDOW_SCHEMA)
            self.assertEqual(response["request"]["days"], 3)
            self.assertEqual(list(Path(td).iterdir()), [])

    def test_cli_does_not_emit_partial_unpublished_window(self):
        with tempfile.TemporaryDirectory() as td:
            stream = StringIO()
            with patch.dict(os.environ, {"STILLPOINT_ROOT": td}, clear=False):
                with redirect_stdout(stream), self.assertRaises(ValueError):
                    main(["calendar-window", "2076",
                          "--start-ordinal", "1", "--days", "1"])
            self.assertEqual(stream.getvalue(), "")
            self.assertEqual(list(Path(td).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
