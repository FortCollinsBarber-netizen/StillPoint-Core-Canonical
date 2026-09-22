import unittest
from datetime import date, timedelta

from stillpoint.calendar_core.models import GeoPoint
from stillpoint.calendar_core.sunset import apparent_sunrise_utc, apparent_sunset_utc
from stillpoint.calendar_core.week import protected_time_state


class ProtectedTimeTests(unittest.TestCase):
    point = GeoPoint(40.3978, -105.0749, "LOVELAND_TEST")
    zone = "America/Denver"

    def test_friday_sunset_opens_sabbath_and_stillpoint(self):
        friday_sunset = apparent_sunset_utc(date(2026, 9, 18), self.point)
        state = protected_time_state(friday_sunset, location=self.point, local_zone=self.zone)
        self.assertEqual(state.named_day, "Saturday")
        self.assertTrue(state.is_sabbath)
        self.assertTrue(state.is_stillpoint)
        self.assertFalse(state.is_lords_day)

    def test_saturday_sunset_opens_lords_day_while_stillpoint_continues(self):
        saturday_sunset = apparent_sunset_utc(date(2026, 9, 19), self.point)
        state = protected_time_state(saturday_sunset, location=self.point, local_zone=self.zone)
        self.assertEqual(state.named_day, "Sunday")
        self.assertFalse(state.is_sabbath)
        self.assertTrue(state.is_lords_day)
        self.assertTrue(state.is_stillpoint)

    def test_sunday_sunrise_releases_stillpoint_not_lords_day(self):
        sunday_sunrise = apparent_sunrise_utc(date(2026, 9, 20), self.point)
        before = protected_time_state(
            sunday_sunrise - timedelta(seconds=1),
            location=self.point,
            local_zone=self.zone,
        )
        at = protected_time_state(sunday_sunrise, location=self.point, local_zone=self.zone)
        self.assertTrue(before.is_stillpoint)
        self.assertTrue(before.is_lords_day)
        self.assertFalse(at.is_stillpoint)
        self.assertTrue(at.is_lords_day)

    def test_sunday_sunset_ends_lords_day(self):
        sunday_sunset = apparent_sunset_utc(date(2026, 9, 20), self.point)
        at = protected_time_state(sunday_sunset, location=self.point, local_zone=self.zone)
        self.assertFalse(at.is_sabbath)
        self.assertFalse(at.is_lords_day)
        self.assertFalse(at.is_stillpoint)


if __name__ == "__main__":
    unittest.main()
