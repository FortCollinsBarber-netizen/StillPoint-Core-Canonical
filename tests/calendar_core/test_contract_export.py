import json
import tempfile
import unittest
from pathlib import Path

from stillpoint.calendar_core.contract import (
    CONTRACT_VERSION,
    build_calendar_core_contract,
    export_calendar_core_contract,
)


class CalendarCoreContractTests(unittest.TestCase):
    def test_contract_is_historical_compatibility_bridge(self):
        doc = build_calendar_core_contract()
        self.assertEqual(doc["version"], CONTRACT_VERSION)
        self.assertEqual(doc["constants"]["baseYearDays"], 364)
        self.assertEqual(doc["constants"]["reconciliationDaysAllowed"], [0])
        observation = next(
            row for row in doc["goldenVectors"]
            if row["id"] == "observation-zero"
        )
        common = observation["expected"]["commonDate"]
        self.assertEqual(common["ordinal"], 260)
        self.assertEqual((common["month"], common["day"]), (9, 17))
        self.assertEqual(common["weekday"], "Thursday")

    def test_export_is_deterministic_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "contract.json"
            export_calendar_core_contract(path)
            first = path.read_bytes()
            export_calendar_core_contract(path)
            second = path.read_bytes()
            self.assertEqual(first, second)
            parsed = json.loads(first)
            self.assertEqual(parsed["version"], CONTRACT_VERSION)


if __name__ == "__main__":
    unittest.main()
