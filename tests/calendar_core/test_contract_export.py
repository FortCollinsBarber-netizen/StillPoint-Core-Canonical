import json
import tempfile
import unittest
from pathlib import Path

from stillpoint.calendar_core.contract import (
    CONTRACT_VERSION,
    build_calendar_core_contract,
    export_calendar_core_contract,
)
from stillpoint.calendar_core.spec import (
    ENGINEERING_INVARIANT,
    SPEC_VERSION,
    build_calendar_core_spec,
    export_calendar_core_spec,
)
from stillpoint.calendar_core.vectors import (
    VECTORS_VERSION,
    build_calendar_projection_vectors,
    export_calendar_projection_vectors,
)


class CalendarArtifactTests(unittest.TestCase):
    def test_stable_spec_contains_law_not_pilot_or_evidence(self):
        doc = build_calendar_core_spec()
        self.assertEqual(doc["version"], SPEC_VERSION)
        self.assertEqual(doc["ordinaryYear"]["days"], 364)
        self.assertEqual(
            doc["ordinaryYear"]["gateSequence"],
            [4, 5, 6, 6, 5, 4, 3, 2, 1, 1, 2, 3],
        )
        self.assertEqual(doc["namespaces"]["reconciliation"]["allowedDays"], [0, 7])
        self.assertEqual(doc["engineeringInvariant"], ENGINEERING_INVARIANT)
        serialized = json.dumps(doc)
        self.assertNotIn("LOVELAND_TEST", serialized)
        self.assertNotIn("jubileeEpoch", serialized)
        self.assertNotIn("ephemerisId", serialized)

    def test_projection_vectors_are_separate_from_law(self):
        doc = build_calendar_projection_vectors()
        self.assertEqual(doc["version"], VECTORS_VERSION)
        self.assertEqual(doc["specVersion"], SPEC_VERSION)
        self.assertEqual(
            doc["referenceStatus"],
            "public-conformance-only-not-ground-zero",
        )
        by_id = {row["id"]: row for row in doc["vectors"]}

        observation = by_id["observation-zero"]["expected"]
        self.assertEqual(observation["continuousK"], 259)
        self.assertEqual(observation["state"], "ORDINARY")
        self.assertEqual(observation["ordinaryAddress"], "Y_2026-260")
        self.assertEqual(observation["commonDate"]["ordinal"], 260)

        r3 = by_id["reconciliation-r3"]["expected"]
        self.assertEqual(r3["state"], "RECONCILIATION")
        self.assertEqual(r3["reconciliationDay"], 3)
        self.assertEqual(r3["reconciliationAddress"], "Y_2026/Y_2027-R3")
        self.assertIsNone(r3["commonDate"])
        self.assertIsNone(r3["annualPhase"])
        self.assertIsNone(r3["solarGate"])

        outside = by_id["outside-publication-range"]["expected"]
        self.assertEqual(outside["state"], "OUTSIDE_RANGE")
        self.assertIsNone(outside["ordinaryAddress"])
        self.assertIsNone(outside["reconciliationAddress"])

    def test_checked_in_spec_and_vectors_are_generated_artifacts(self):
        root = Path(__file__).resolve().parents[2]
        checked_spec = json.loads(
            (root / "stillpoint/contracts/calendar_core_spec.json").read_text(
                encoding="utf-8"
            )
        )
        checked_vectors = json.loads(
            (
                root
                / "stillpoint/contracts/calendar_projection_vectors.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(checked_spec, build_calendar_core_spec())
        self.assertEqual(checked_vectors, build_calendar_projection_vectors())

    def test_legacy_aggregate_is_explicitly_deprecated(self):
        doc = build_calendar_core_contract()
        self.assertEqual(doc["version"], CONTRACT_VERSION)
        self.assertTrue(doc["deprecated"])
        self.assertEqual(
            doc["replacementArtifacts"],
            [
                "calendar_core_spec.json",
                "calendar_publication.json",
                "calendar_projection_vectors.json",
            ],
        )

    def test_exports_are_deterministic_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            targets = [
                (root / "spec.json", export_calendar_core_spec, SPEC_VERSION),
                (
                    root / "vectors.json",
                    export_calendar_projection_vectors,
                    VECTORS_VERSION,
                ),
                (root / "legacy.json", export_calendar_core_contract, CONTRACT_VERSION),
            ]
            for path, exporter, expected_version in targets:
                exporter(path)
                first = path.read_bytes()
                exporter(path)
                second = path.read_bytes()
                self.assertEqual(first, second)
                self.assertEqual(json.loads(first)["version"], expected_version)


if __name__ == "__main__":
    unittest.main()
