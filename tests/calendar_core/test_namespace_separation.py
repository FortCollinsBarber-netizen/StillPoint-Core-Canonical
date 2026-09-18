import unittest

import stillpoint.calendar_core as calendar_core
import stillpoint.temporal as temporal_authority


class NamespaceSeparationTests(unittest.TestCase):
    def test_calendar_does_not_overwrite_temporal_authority(self):
        self.assertTrue(hasattr(temporal_authority, "Claim"))
        self.assertTrue(hasattr(temporal_authority, "Warrant"))
        self.assertTrue(hasattr(calendar_core, "CalendarSnapshot"))
        self.assertFalse(hasattr(calendar_core, "Claim"))


if __name__ == "__main__":
    unittest.main()
