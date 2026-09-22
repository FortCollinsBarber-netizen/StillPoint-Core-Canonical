import unittest

import stillpoint.calendar_core as calendar_core
import stillpoint.calendar_publication as calendar_publication
import stillpoint.calendar_witness as calendar_witness
import stillpoint.temporal as temporal_authority


class NamespaceSeparationTests(unittest.TestCase):
    def test_calendar_does_not_overwrite_temporal_authority(self):
        self.assertTrue(hasattr(temporal_authority, "Claim"))
        self.assertTrue(hasattr(temporal_authority, "Warrant"))
        self.assertTrue(hasattr(calendar_core, "CalendarSnapshot"))
        self.assertFalse(hasattr(calendar_core, "Claim"))

    def test_publication_and_witness_are_not_top_level_calendar_law(self):
        self.assertTrue(hasattr(calendar_publication, "compile_v33_publication"))
        self.assertTrue(hasattr(calendar_witness, "jubilee_state"))
        self.assertFalse(hasattr(calendar_core, "jubilee_state"))
        self.assertFalse(hasattr(calendar_core, "select_v33_nearest_spring_gate"))


if __name__ == "__main__":
    unittest.main()
