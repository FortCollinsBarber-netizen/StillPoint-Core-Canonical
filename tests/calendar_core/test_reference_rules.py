import unittest
from datetime import date

from stillpoint.calendar_core.models import GeoPoint
from stillpoint.calendar_core.reference_rule import (
    spring_gate_date,
    select_v32_nearest_legal,
    select_v33_nearest_spring_gate,
)
from stillpoint.calendar_core.sunset import apparent_sunset_utc


class ReferenceRuleTests(unittest.TestCase):
    point = GeoPoint(40.4, -105.1, "REFERENCE_TEST")

    def test_v32_is_preserved_as_explicit_version(self):
        opening = date(2026, 1, 1)
        candidate = opening.fromordinal(opening.toordinal() + 364)
        equinox = apparent_sunset_utc(candidate, self.point)
        decision = select_v32_nearest_legal(
            current_opening=opening,
            next_march_equinox=equinox,
            reference_point=self.point,
        )
        self.assertEqual(decision.version, "v3.2")
        self.assertEqual(decision.operator, "NearestLegal")
        self.assertEqual(decision.reconciliation_days, 0)
        self.assertIn(decision.legacy_elapsed_span_days, (364, 371))

    def test_v33_spring_gate_keeps_ordinary_year_364(self):
        opening = date(2026, 1, 1)
        next_opening = opening.fromordinal(opening.toordinal() + 364)
        gate = spring_gate_date(next_opening)
        equinox = apparent_sunset_utc(gate, self.point)
        decision = select_v33_nearest_spring_gate(
            current_opening=opening,
            next_march_equinox=equinox,
            reference_point=self.point,
        )
        self.assertEqual(decision.version, "v3.3-candidate")
        self.assertEqual(decision.operator, "NearestLegalSpringGate")
        self.assertEqual(decision.reconciliation_days, 0)
        self.assertEqual((decision.immediate_candidate_opening - opening).days, 364)

    def test_v33_delayed_candidate_is_exactly_one_week(self):
        opening = date(2026, 1, 1)
        delayed_opening = opening.fromordinal(opening.toordinal() + 371)
        delayed_gate = spring_gate_date(delayed_opening)
        equinox = apparent_sunset_utc(delayed_gate, self.point)
        decision = select_v33_nearest_spring_gate(
            current_opening=opening,
            next_march_equinox=equinox,
            reference_point=self.point,
        )
        self.assertEqual(decision.reconciliation_days, 7)
        self.assertEqual(
            (decision.delayed_candidate_opening - decision.immediate_candidate_opening).days,
            7,
        )


if __name__ == "__main__":
    unittest.main()
