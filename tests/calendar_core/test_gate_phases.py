import unittest

from stillpoint.calendar_core.gates import GATE_SEQUENCE, PHASE_LENGTHS, phase_for_base_day


class GatePhaseTests(unittest.TestCase):
    def test_recovered_six_paired_gate_sequence(self):
        self.assertEqual(GATE_SEQUENCE, (4, 5, 6, 6, 5, 4, 3, 2, 1, 1, 2, 3))
        self.assertEqual(PHASE_LENGTHS, (30, 30, 31) * 4)
        self.assertEqual(sum(PHASE_LENGTHS), 364)
        self.assertEqual(set(GATE_SEQUENCE), {1, 2, 3, 4, 5, 6})

    def test_phase_boundaries(self):
        self.assertEqual(phase_for_base_day(1).phase, 1)
        self.assertEqual(phase_for_base_day(30).gate, 4)
        self.assertEqual(phase_for_base_day(31).gate, 5)
        self.assertEqual(phase_for_base_day(91).phase, 3)
        self.assertEqual(phase_for_base_day(364).phase, 12)


if __name__ == "__main__":
    unittest.main()
