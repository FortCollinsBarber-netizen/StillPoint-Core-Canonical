from __future__ import annotations

import json
import unittest
from pathlib import Path

from stillpoint.calendar_core.calendar import (
    CANONICAL_DAY001_WEEKDAY,
    MONTH_LENGTHS,
    weekday_for_ordinal,
)


RATIFICATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "stillpoint"
    / "contracts"
    / "calendar_ratification_v1.json"
)


class CalendarRatificationLockTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads(
            RATIFICATION_PATH.read_text(encoding="utf-8")
        )

    def test_ratification_is_enacted_and_matches_executable_grid(self):
        doc = self.document
        calendar = doc["calendar"]

        self.assertEqual(doc["status"], "enacted")
        self.assertEqual(calendar["yearDays"], 364)
        self.assertEqual(calendar["weekDays"], 7)
        self.assertEqual(calendar["weeksPerYear"], 52)
        self.assertEqual(sum(MONTH_LENGTHS), 364)

        self.assertEqual(
            calendar["yearOpening"],
            {"month": 1, "day": 1, "weekday": "Thursday"},
        )
        self.assertEqual(
            calendar["yearClosing"],
            {"month": 12, "day": 30, "weekday": "Wednesday"},
        )
        self.assertEqual(CANONICAL_DAY001_WEEKDAY, "Thursday")
        self.assertEqual(weekday_for_ordinal(364), "Wednesday")

        self.assertFalse(calendar["december31Exists"])
        self.assertFalse(calendar["february29Exists"])
        self.assertFalse(calendar["leapYears"])
        self.assertEqual(calendar["mapYears"], 50)
        self.assertEqual(calendar["totalMappedDays"], 18_200)

    def test_clock_keeps_24_hour_coordination_without_dst(self):
        clock = self.document["clock"]
        self.assertEqual(clock["format"], "24-hour-retained")
        self.assertFalse(clock["daylightSavingTime"])
        self.assertEqual(
            clock["commonClockPolicy"],
            "permanent-standard-time",
        )
        self.assertEqual(
            clock["midnightRole"],
            "civil-coordinate-date-boundary",
        )
        self.assertFalse(clock["ontologicalAuthority"])

    def test_witness_and_external_projection_cannot_mutate_grid(self):
        projection = self.document["externalProjection"]
        self.assertEqual(
            projection["purpose"],
            "interoperability-with-existing-gregorian-systems",
        )
        self.assertEqual(
            projection["frame"],
            "proleptic-gregorian",
        )
        self.assertFalse(projection["gridAuthority"])
        self.assertFalse(projection["mayMoveCommonDates"])
        self.assertFalse(projection["mayInsertDays"])

        for value in self.document["witnessPolicy"].values():
            self.assertIn("no-grid-mutation", value)

    def test_superseded_reconciliation_models_are_non_operational(self):
        supersession = self.document["supersession"]
        self.assertEqual(supersession["reconciliation"], "non-operative")
        self.assertEqual(supersession["intercalation"], "none")
        self.assertEqual(
            supersession["nearestLegalV32"],
            "historical-only",
        )
        self.assertEqual(
            supersession["nearestLegalSpringGateV33"],
            "historical-only",
        )


if __name__ == "__main__":
    unittest.main()
