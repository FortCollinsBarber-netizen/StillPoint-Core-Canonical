"""Public calendar consumer process-isolation regression.

The installed Core CLI must serve published calendar data without a company
database, provider credentials, private checkout, or writable project state.
This exercises a clean external process instead of an in-process mock and
does not attempt to qualify any private RobertOS/StillPointOS integration.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class PublicCalendarIsolatedConsumerTests(unittest.TestCase):
    def _run_in_empty_directory(self, year: int, ordinal: int) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="stillpoint-public-consumer-") as td:
            root = Path(td)
            env = os.environ.copy()
            env["STILLPOINT_ROOT"] = str(root)
            env["STILLPOINT_PROVIDER"] = "mock"
            # Public read-only calendar access must not depend on live provider keys.
            for key in ("OPENAI_API_KEY", "XAI_API_KEY", "ANTHROPIC_API_KEY"):
                env.pop(key, None)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "stillpoint.cli",
                    "calendar-day",
                    str(year),
                    "--ordinal",
                    str(ordinal),
                ],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                check=False,
                timeout=45,
            )
            self.assertEqual(
                list(root.iterdir()),
                [],
                "Read-only calendar CLI must not write company state or files to an empty operator root",
            )
            return result

    def test_published_first_and_last_days_work_without_writable_state(self):
        for year, ordinal, expected in (
            (2026, 1, "Y_2026-001"),
            (2075, 364, "Y_2075-364"),
        ):
            with self.subTest(year=year, ordinal=ordinal):
                result = self._run_in_empty_directory(year, ordinal)
                self.assertEqual(result.returncode, 0, result.stderr)
                value = json.loads(result.stdout)
                self.assertEqual(value["schema"], "stillpoint.calendar-day.v2")
                self.assertEqual(value["authority"], "read-only-calendar-law")
                self.assertEqual(value["calendar_address"], expected)
                self.assertEqual(value["map"]["first_year"], 2026)
                self.assertEqual(value["map"]["last_year"], 2075)

    def test_unpublished_next_year_fails_without_creating_state(self):
        result = self._run_in_empty_directory(2076, 1)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(result.stdout.strip(), "An unpublished year must not emit a calendar payload")


if __name__ == "__main__":
    unittest.main()
