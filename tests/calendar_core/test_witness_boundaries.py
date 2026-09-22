import unittest
from datetime import datetime, timezone

from stillpoint.calendar_core import build_calendar_core_spec
from stillpoint.calendar_core.witness import (
    LunarWitness,
    SeasonGateWitness,
    WitnessValidationError,
    as_march_equinox_evidence,
)


class WitnessBoundaryTests(unittest.TestCase):
    digest = "a" * 64

    def test_lunar_witness_is_evidence_only(self):
        before = build_calendar_core_spec()
        witness = LunarWitness(
            phase="full",
            instant_utc=datetime(
                2026, 9, 26, 16, 49, tzinfo=timezone.utc
            ),
            source_id="TEST_LUNAR",
            evidence_sha256=self.digest,
            reference_id="GROUND_ZERO_PILOT",
        )
        self.assertEqual(witness.phase, "full")
        self.assertEqual(build_calendar_core_spec(), before)

    def test_lunar_witness_cannot_smuggle_invalid_digest(self):
        with self.assertRaises(WitnessValidationError):
            LunarWitness(
                phase="new",
                instant_utc=datetime.now(timezone.utc),
                source_id="TEST",
                evidence_sha256="not-a-digest",
            )

    def test_gate_position_and_direction_are_distinct(self):
        witness = SeasonGateWitness(
            event="seasonal_gate_observation",
            year=2026,
            instant_utc=datetime(
                2026, 9, 22, 0, 0, tzinfo=timezone.utc
            ),
            source_id="TEST_SOLAR",
            evidence_sha256=self.digest,
            reference_frame="local-horizon",
            gate_position=3,
            direction_of_travel="southward",
        )
        self.assertEqual(witness.gate_position, 3)
        self.assertEqual(witness.direction_of_travel, "southward")

    def test_spring_gate_bridge_is_explicit_and_preserves_provenance(self):
        witness = SeasonGateWitness(
            event="march_equinox",
            year=2027,
            instant_utc=datetime(
                2027, 3, 20, 12, 0, tzinfo=timezone.utc
            ),
            source_id="TEST_EPHEMERIS",
            evidence_sha256=self.digest,
            reference_frame="geocentric-equatorial",
            gate_position=None,
            direction_of_travel="northward",
        )
        evidence = as_march_equinox_evidence(witness)
        self.assertEqual(evidence.event, "march_equinox")
        self.assertEqual(evidence.year, 2027)
        self.assertEqual(evidence.source_id, "TEST_EPHEMERIS")
        self.assertEqual(evidence.evidence_sha256, self.digest)

    def test_non_equinox_witness_cannot_enter_reference_rule_bridge(self):
        witness = SeasonGateWitness(
            event="september_equinox",
            year=2026,
            instant_utc=datetime(
                2026, 9, 23, 0, 5, tzinfo=timezone.utc
            ),
            source_id="TEST_EPHEMERIS",
            evidence_sha256=self.digest,
            reference_frame="geocentric-equatorial",
            gate_position=None,
            direction_of_travel="southward",
        )
        with self.assertRaises(WitnessValidationError):
            as_march_equinox_evidence(witness)

    def test_witnesses_do_not_ratify_unresolved_enactment_inputs(self):
        spec = build_calendar_core_spec()
        self.assertEqual(
            spec["enactmentBoundary"]["status"],
            "external-unresolved",
        )
        self.assertTrue(
            spec["enactmentBoundary"]["lawDoesNotSupplyValues"],
        )


if __name__ == "__main__":
    unittest.main()
