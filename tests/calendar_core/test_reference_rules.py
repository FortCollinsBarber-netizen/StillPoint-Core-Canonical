import unittest
from datetime import date, datetime, timedelta, timezone

from stillpoint.calendar_core.astronomy import (
    AstronomyEvidence,
    AstronomyEvidenceError,
    MappingAstronomyProvider,
)
from stillpoint.calendar_core.models import GeoPoint
from stillpoint.calendar_core.reference_rule import (
    spring_gate_date,
    select_v32_nearest_legal,
    select_v33_nearest_spring_gate,
    select_v33_nearest_spring_gate_from_evidence,
    select_v33_nearest_spring_gate_from_provider,
)
from stillpoint.calendar_core.sunset import apparent_sunset_utc


class ReferenceRuleTests(unittest.TestCase):
    point = GeoPoint(40.4, -105.1, "REFERENCE_TEST")

    def _evidence(
        self,
        *,
        year: int,
        instant: datetime,
        source: str = "TEST_EPHEMERIS",
    ) -> AstronomyEvidence:
        return AstronomyEvidence(
            event="march_equinox",
            year=year,
            instant_utc=instant,
            source_id=source,
            evidence_sha256="a" * 64,
        )

    def test_v32_is_preserved_as_explicit_version(self):
        opening = date(2026, 1, 1)
        candidate = opening + timedelta(days=364)
        equinox = apparent_sunset_utc(candidate, self.point)
        decision = select_v32_nearest_legal(
            current_opening=opening,
            next_march_equinox=equinox,
            reference_point=self.point,
        )
        self.assertEqual(decision.version, "v3.2")
        self.assertEqual(decision.operator, "NearestLegal")
        self.assertEqual(decision.reconciliation_days, 0)
        self.assertEqual(
            decision.reason_code,
            "IMMEDIATE_CLOSER_OR_TIE",
        )
        self.assertIn(
            decision.legacy_elapsed_span_days,
            (364, 371),
        )

    def test_v33_spring_gate_keeps_ordinary_year_364(self):
        opening = date(2026, 1, 1)
        next_opening = opening + timedelta(days=364)
        gate = spring_gate_date(next_opening)
        evidence = self._evidence(
            year=2027,
            instant=apparent_sunset_utc(gate, self.point),
        )
        decision = select_v33_nearest_spring_gate_from_evidence(
            current_opening=opening,
            evidence=evidence,
            expected_evidence_year=2027,
            reference_point=self.point,
        )
        self.assertEqual(
            decision.version,
            "v3.3-candidate",
        )
        self.assertEqual(
            decision.operator,
            "NearestLegalSpringGate",
        )
        self.assertEqual(
            decision.reconciliation_days,
            0,
        )
        self.assertEqual(
            decision.reason_code,
            "IMMEDIATE_CLOSER_OR_TIE",
        )
        self.assertEqual(
            (
                decision.immediate_candidate_opening
                - opening
            ).days,
            364,
        )
        self.assertEqual(
            decision.evidence_source_id,
            "TEST_EPHEMERIS",
        )

    def test_v33_delayed_candidate_is_exactly_one_week(self):
        opening = date(2026, 1, 1)
        delayed_opening = opening + timedelta(days=371)
        delayed_gate = spring_gate_date(delayed_opening)
        evidence = self._evidence(
            year=2027,
            instant=apparent_sunset_utc(
                delayed_gate,
                self.point,
            ),
        )
        decision = select_v33_nearest_spring_gate_from_evidence(
            current_opening=opening,
            evidence=evidence,
            expected_evidence_year=2027,
            reference_point=self.point,
        )
        self.assertEqual(
            decision.reconciliation_days,
            7,
        )
        self.assertEqual(
            decision.reason_code,
            "RECONCILIATION_WEEK_CLOSER",
        )
        self.assertEqual(
            (
                decision.delayed_candidate_opening
                - decision.immediate_candidate_opening
            ).days,
            7,
        )
        self.assertEqual(
            (
                decision.immediate_candidate_opening
                - opening
            ).days,
            364,
        )

    def test_provider_requires_explicit_evidence_year(self):
        opening = date(2026, 1, 1)
        gate = spring_gate_date(
            opening + timedelta(days=364)
        )
        evidence = self._evidence(
            year=2027,
            instant=apparent_sunset_utc(gate, self.point),
        )
        provider = MappingAstronomyProvider(
            provider_id="TEST_EPHEMERIS",
            evidence_by_year={2027: evidence},
        )
        decision = select_v33_nearest_spring_gate_from_provider(
            current_opening=opening,
            evidence_year=2027,
            provider=provider,
            reference_point=self.point,
        )
        self.assertEqual(
            decision.reconciliation_days,
            0,
        )
        self.assertEqual(
            decision.evidence_sha256,
            "a" * 64,
        )

    def test_missing_provider_evidence_fails_closed(self):
        provider = MappingAstronomyProvider(
            provider_id="TEST_EPHEMERIS",
            evidence_by_year={},
        )
        with self.assertRaises(AstronomyEvidenceError) as raised:
            select_v33_nearest_spring_gate_from_provider(
                current_opening=date(2026, 1, 1),
                evidence_year=2027,
                provider=provider,
                reference_point=self.point,
            )
        self.assertEqual(
            raised.exception.code,
            "MISSING_ASTRONOMY_EVIDENCE",
        )

    def test_naive_astronomical_evidence_fails_closed(self):
        with self.assertRaises(AstronomyEvidenceError) as raised:
            AstronomyEvidence(
                event="march_equinox",
                year=2027,
                instant_utc=datetime(
                    2027,
                    3,
                    20,
                    12,
                    0,
                ),
                source_id="TEST_EPHEMERIS",
                evidence_sha256="a" * 64,
            )
        self.assertEqual(
            raised.exception.code,
            "NAIVE_ASTRONOMICAL_INSTANT",
        )

    def test_wrong_event_fails_closed(self):
        with self.assertRaises(AstronomyEvidenceError) as raised:
            AstronomyEvidence(
                event="june_solstice",
                year=2027,
                instant_utc=datetime(
                    2027,
                    6,
                    21,
                    12,
                    0,
                    tzinfo=timezone.utc,
                ),
                source_id="TEST_EPHEMERIS",
                evidence_sha256="a" * 64,
            )
        self.assertEqual(
            raised.exception.code,
            "UNSUPPORTED_ASTRONOMICAL_EVENT",
        )

    def test_wrong_evidence_year_fails_closed(self):
        opening = date(2026, 1, 1)
        evidence = self._evidence(
            year=2028,
            instant=datetime(
                2028,
                3,
                20,
                12,
                0,
                tzinfo=timezone.utc,
            ),
        )
        with self.assertRaises(AstronomyEvidenceError) as raised:
            select_v33_nearest_spring_gate_from_evidence(
                current_opening=opening,
                evidence=evidence,
                expected_evidence_year=2027,
                reference_point=self.point,
            )
        self.assertEqual(
            raised.exception.code,
            "ASTRONOMY_EVIDENCE_YEAR_MISMATCH",
        )

    def test_common_year_label_does_not_choose_evidence_year(self):
        opening = date(2026, 1, 1)
        gate = spring_gate_date(
            opening + timedelta(days=364)
        )
        evidence = self._evidence(
            year=2027,
            instant=apparent_sunset_utc(gate, self.point),
        )
        provider = MappingAstronomyProvider(
            provider_id="TEST_EPHEMERIS",
            evidence_by_year={2027: evidence},
        )

        # The provider takes an explicitly named astronomical year; no Common
        # Calendar year label participates in this call.
        decision = select_v33_nearest_spring_gate_from_provider(
            current_opening=opening,
            evidence_year=2027,
            provider=provider,
            reference_point=self.point,
        )
        self.assertEqual(decision.evidence_year, 2027)

    def test_direct_compatibility_entrypoint_remains_named(self):
        opening = date(2026, 1, 1)
        gate = spring_gate_date(
            opening + timedelta(days=364)
        )
        decision = select_v33_nearest_spring_gate(
            current_opening=opening,
            next_march_equinox=apparent_sunset_utc(
                gate,
                self.point,
            ),
            reference_point=self.point,
        )
        self.assertEqual(
            decision.operator,
            "NearestLegalSpringGate",
        )
        self.assertEqual(
            decision.evidence_source_id,
            "DIRECT_CALL_UNCUSTODIED",
        )

    def test_v33_invariants_across_many_years(self):
        opening = date(2020, 1, 1)
        for index in range(50):
            immediate = opening + timedelta(days=364)
            delayed = immediate + timedelta(days=7)

            target_opening = (
                immediate
                if index % 2 == 0
                else delayed
            )
            target_gate = spring_gate_date(
                target_opening
            )
            evidence_year = target_gate.year
            evidence = self._evidence(
                year=evidence_year,
                instant=apparent_sunset_utc(
                    target_gate,
                    self.point,
                ),
            )
            decision = select_v33_nearest_spring_gate_from_evidence(
                current_opening=opening,
                evidence=evidence,
                expected_evidence_year=evidence_year,
                reference_point=self.point,
            )

            self.assertEqual(
                (
                    decision.immediate_candidate_opening
                    - opening
                ).days,
                364,
            )
            self.assertEqual(
                (
                    decision.delayed_candidate_opening
                    - decision.immediate_candidate_opening
                ).days,
                7,
            )
            self.assertIn(
                decision.reconciliation_days,
                (0, 7),
            )
            self.assertEqual(
                decision.legacy_elapsed_span_days % 7,
                0,
            )

            opening = (
                decision.selected_candidate_opening
            )


if __name__ == "__main__":
    unittest.main()
