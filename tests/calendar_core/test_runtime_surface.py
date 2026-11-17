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
from stillpoint.calendar_core.long_cycles import JubileeConfiguration
from stillpoint.cli import main


class CalendarRuntimeSurfaceTests(unittest.TestCase):
    def test_day_one_is_exact_fixed_map_address(self):
        value = calendar_day_payload(2026, 1)
        self.assertEqual(value["schema"], "stillpoint.calendar-day.v2")
        self.assertEqual(value["authority"], "read-only-calendar-law")
        self.assertEqual(value["calendar_address"], "Y_2026-001")
        self.assertEqual(value["common_date"]["year"], 2026)
        self.assertEqual(value["common_date"]["ordinal"], 1)
        self.assertEqual(value["common_date"]["weekday"], "Thursday")
        self.assertEqual(value["common_civil_coordinate"]["date"], "2026-01-01")
        self.assertEqual(value["common_civil_coordinate"]["clock"], "24-hour")
        self.assertFalse(value["common_civil_coordinate"]["daylight_saving_time"])
        self.assertEqual(value["civil_window"]["opens"], "2026-01-01")
        self.assertEqual(value["civil_window"]["role"], "external-translation-only")
        self.assertFalse(value["civil_window"]["grid_authority"])
        self.assertEqual(value["map"]["year_days"], 364)
        self.assertEqual(value["map"]["weeks_per_year"], 52)
        self.assertFalse(value["map"]["december_31_exists"])
        self.assertEqual(value["map"]["year_count"], 50)
        self.assertEqual(value["map"]["total_days"], 18200)

    def test_last_published_year_remains_same_grid_and_reports_year_49(self):
        value = calendar_day_payload(2075, 1)
        self.assertEqual(value["calendar_address"], "Y_2075-001")
        self.assertEqual(value["common_civil_coordinate"]["date"], "2075-01-01")
        self.assertFalse(value["jubilee"]["is_jubilee_year"])
        self.assertEqual(value["jubilee"]["year"], 49)
        self.assertEqual(value["publication"]["authority_status"], "enacted")

    def test_explicit_cycle_comparison_cannot_inherit_author_selection(self):
        selected = calendar_day_payload(2075, 1)
        self.assertEqual(
            selected["jubilee"]["configuration"]["decision_status"],
            "author-selected-working-rule-not-civil-enactment",
        )
        self.assertTrue(selected["jubilee"]["configuration"]["selected_policy_applies"])

        comparison = calendar_day_payload(
            2075, 1,
            jubilee_configuration=JubileeConfiguration(
                epoch_common_year=2026, rollover_rule="standalone-50",
            ),
        )
        self.assertEqual(
            comparison["jubilee"]["configuration"]["selection_source"],
            "explicit-call-configuration",
        )
        self.assertEqual(
            comparison["jubilee"]["configuration"]["decision_status"],
            "explicit-comparison-input-not-author-selected",
        )
        self.assertEqual(
            comparison["jubilee"]["release_day_projection_status"],
            "computed-under-explicit-comparison-not-author-selected",
        )
        self.assertFalse(
            comparison["jubilee"]["configuration"]["selected_policy_applies"]
        )
        # Top-level policy remains an informational description of the
        # author-selected default; it is not an endorsement of the override.
        self.assertEqual(
            comparison["long_cycle_policy"]["selectionStatus"],
            "author-selected-working-rule-not-civil-enactment",
        )
        unconfigured = calendar_day_payload(
            2027, 1, jubilee_configuration=JubileeConfiguration(epoch_common_year=None)
        )
        self.assertEqual(unconfigured["jubilee"]["designation_status"], "unconfigured-epoch")
        self.assertFalse(unconfigured["jubilee"]["configuration"]["selected_policy_applies"])

    def test_outside_publication_fails_closed(self):
        with self.assertRaises(ValueError):
            calendar_day_payload(2076, 1)

    def test_cli_calendar_read_does_not_open_company_runtime(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            stream = StringIO()
            with patch.dict(os.environ, {"STILLPOINT_ROOT": str(root)}, clear=False):
                with redirect_stdout(stream):
                    code = main(["calendar-day", "2026", "--ordinal", "1"])
            self.assertEqual(code, 0)
            payload = json.loads(stream.getvalue())
            self.assertEqual(payload["calendar_address"], "Y_2026-001")
            self.assertFalse((root / "state" / "company.sqlite").exists())


if __name__ == "__main__":
    unittest.main()
