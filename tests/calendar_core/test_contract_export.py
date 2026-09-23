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
    def test_contract_is_non_authoritative_v2_bridge(self):
        doc = build_calendar_core_contract()
        self.assertEqual(doc["version"], CONTRACT_VERSION)
        constants = doc["constants"]
        self.assertEqual(constants["baseYearDays"], 364)
        self.assertEqual(constants["weeksPerYear"], 52)
        self.assertEqual(constants["day001Weekday"], "Thursday")
        self.assertEqual(
            constants["monthLengths"],
            [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 30],
        )
        self.assertEqual(constants["seasonalQuarterDays"], 91)
        self.assertEqual(
            doc["jurisdiction"]["authorityStatus"],
            "non-authoritative-compatibility-only",
        )

    def test_observation_zero_separates_common_date_from_named_protected_day(self):
        doc = build_calendar_core_contract()
        observation = next(
            row
            for row in doc["goldenVectors"]
            if row["id"] == "observation-zero"
        )
        expected = observation["expected"]
        common = expected["commonDate"]
        self.assertEqual(common["ordinal"], 261)
        self.assertEqual((common["month"], common["day"]), (9, 18))
        self.assertEqual(common["weekday"], "Friday")
        self.assertEqual(expected["namedDay"], "Friday")
        self.assertEqual(expected["annualPhase"], 9)
        self.assertEqual(expected["solarGate"], 1)

    def test_weekly_transition_vectors(self):
        doc = build_calendar_core_contract()
        by_id = {
            row["id"]: row["expected"]
            for row in doc["goldenVectors"]
        }
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
