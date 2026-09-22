import unittest
from datetime import date, datetime, timezone

from stillpoint.calendar_core.models import GeoPoint
from stillpoint.calendar_core.service import CalendarConfig, get_calendar_snapshot


class CalendarServiceTests(unittest.TestCase):
    def test_observation_zero_snapshot_is_pure_calendar_projection(self):
        config = CalendarConfig(
            location=GeoPoint(40.3978, -105.0749, "LOVELAND_TEST"),
            local_zone="America/Denver",
            common_year=2026,
            opening_civil_date=date(2026, 1, 1),
            day001_weekday="Friday",
            common_standard_offset_seconds=-7 * 3600,
        )
        snap = get_calendar_snapshot(
            datetime(2026, 9, 18, 19, 28, 57, tzinfo=timezone.utc),
            config=config,
        )
        self.assertEqual(snap.state, "ORDINARY")
        self.assertEqual(snap.continuous_k, 259)
        self.assertEqual(snap.ordinary_address, "Y_2026-260")
        self.assertEqual(snap.common_date.ordinal, 260)
        self.assertEqual(snap.common_date.weekday, "Friday")
        self.assertEqual(snap.annual_phase, 9)
        self.assertEqual(snap.solar_gate, 1)
        self.assertFalse(hasattr(snap, "jubilee"))
        self.assertFalse(hasattr(snap, "ephemeris_id"))
        self.assertFalse(hasattr(snap, "reference_station_id"))


if __name__ == "__main__":
    unittest.main()
