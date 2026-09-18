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
    def test_contract_constants_and_observation_zero(self):
        doc = build_calendar_core_contract()
        self.assertEqual(doc["version"], CONTRACT_VERSION)
        self.assertEqual(doc["constants"]["baseYearDays"], 364)
        self.assertEqual(
            doc["constants"]["gateSequence"],
            [4, 5, 6, 6, 5, 4, 3, 2, 1, 1, 2, 3],
        )
        self.assertEqual(doc["constants"]["reconciliationDaysAllowed"], [0, 7])

        observation = next(
            row for row in doc["goldenVectors"]
            if row["id"] == "observation-zero"
        )
        common = observation["expected"]["commonDate"]
        self.assertEqual(common["ordinal"], 260)
        self.assertEqual((common["month"], common["day"]), (9, 18))
        self.assertEqual(common["weekday"], "Friday")
        self.assertEqual(observation["expected"]["annualPhase"], 9)
        self.assertEqual(observation["expected"]["solarGate"], 1)

    def test_weekly_transition_vectors(self):
        doc = build_calendar_core_contract()
        by_id = {row["id"]: row["expected"] for row in doc["goldenVectors"]}

        self.assertTrue(by_id["friday-after-sunset"]["sabbath"])
        self.assertTrue(by_id["friday-after-sunset"]["stillPoint"])

        self.assertTrue(by_id["saturday-after-sunset"]["lordsDay"])
        self.assertTrue(by_id["saturday-after-sunset"]["stillPoint"])

        self.assertTrue(by_id["sunday-before-sunrise"]["stillPoint"])
        self.assertFalse(by_id["sunday-after-sunrise"]["stillPoint"])
        self.assertTrue(by_id["sunday-after-sunrise"]["lordsDay"])

        self.assertFalse(by_id["sunday-after-sunset"]["lordsDay"])

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
