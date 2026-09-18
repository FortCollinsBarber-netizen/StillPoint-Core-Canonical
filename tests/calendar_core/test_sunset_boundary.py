import unittest
from datetime import date, datetime, timezone

from stillpoint.calendar_core.models import GeoPoint
from stillpoint.calendar_core.sunset import (
    apparent_sunrise_utc,
    apparent_sunset_utc,
    bracket_sunset,
)


class SunsetBoundaryTests(unittest.TestCase):
    point = GeoPoint(40.3978, -105.0749, "LOVELAND_TEST")

    def test_colorado_sunset_can_roll_to_next_utc_date(self):
        event = apparent_sunset_utc(date(2026, 9, 18), self.point)
        self.assertEqual(event.date(), date(2026, 9, 19))
        self.assertGreaterEqual(event.hour, 0)
        self.assertLess(event.hour, 3)

    def test_sunrise_precedes_sunset_for_requested_civil_date(self):
        sunrise = apparent_sunrise_utc(date(2026, 9, 20), self.point)
        sunset = apparent_sunset_utc(date(2026, 9, 20), self.point)
        self.assertLess(sunrise, sunset)

    def test_observation_zero_brackets_from_prior_civil_sunset(self):
        now = datetime(2026, 9, 18, 19, 28, 57, tzinfo=timezone.utc)
        pair = bracket_sunset(now, self.point, "America/Denver")
        self.assertEqual(pair.previous_civil_date, date(2026, 9, 17))
        self.assertEqual(pair.next_civil_date, date(2026, 9, 18))


if __name__ == "__main__":
    unittest.main()
