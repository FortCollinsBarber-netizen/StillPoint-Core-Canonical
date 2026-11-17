import unittest
from datetime import date, timedelta

from stillpoint.calendar_core.models import GeoPoint
from stillpoint.calendar_core.sunset import (
    apparent_sunrise_utc,
    apparent_sunset_utc,
    civil_dawn_utc,
    civil_dusk_utc,
)
from stillpoint.calendar_core.week import (
    protected_time_state,
    protected_time_state_for_common_date,
)


class ProtectedTimeTests(unittest.TestCase):
    point = GeoPoint(40.3978, -105.0749, "LOVELAND_TEST")
    zone = "America/Denver"

    def test_friday_sunset_opens_sabbath_not_civic_stillpoint(self):
        friday = date(2026, 9, 18)
        sunset = apparent_sunset_utc(friday, self.point)
        dusk = civil_dusk_utc(friday, self.point)
        self.assertLess(sunset, dusk)

        at_sunset = protected_time_state(
            sunset, location=self.point, local_zone=self.zone
        )
        self.assertEqual(at_sunset.named_day, "Saturday")
        self.assertTrue(at_sunset.is_sabbath)
        self.assertFalse(at_sunset.is_stillpoint)

        at_dusk = protected_time_state(
            dusk, location=self.point, local_zone=self.zone
        )
        self.assertTrue(at_dusk.is_sabbath)
        self.assertTrue(at_dusk.is_stillpoint)

    def test_saturday_sunset_opens_lords_day_while_civic_stillpoint_continues(self):
        saturday_sunset = apparent_sunset_utc(date(2026, 9, 19), self.point)
        state = protected_time_state(
            saturday_sunset, location=self.point, local_zone=self.zone
        )
        self.assertEqual(state.named_day, "Sunday")
        self.assertFalse(state.is_sabbath)
        self.assertTrue(state.is_lords_day)
        self.assertTrue(state.is_stillpoint)

    def test_sunday_civil_dawn_releases_civic_stillpoint_before_sunrise(self):
        sunday = date(2026, 9, 20)
        dawn = civil_dawn_utc(sunday, self.point)
        sunrise = apparent_sunrise_utc(sunday, self.point)
        self.assertLess(dawn, sunrise)
        before = protected_time_state(
            dawn - timedelta(seconds=1), location=self.point, local_zone=self.zone
        )
        at = protected_time_state(
            dawn, location=self.point, local_zone=self.zone
        )
        self.assertTrue(before.is_stillpoint)
        self.assertTrue(before.is_lords_day)
        self.assertFalse(at.is_stillpoint)
        self.assertTrue(at.is_lords_day)

    def test_sunday_sunset_ends_lords_day(self):
        sunday_sunset = apparent_sunset_utc(date(2026, 9, 20), self.point)
        state = protected_time_state(
            sunday_sunset, location=self.point, local_zone=self.zone
        )
        self.assertFalse(state.is_sabbath)
        self.assertFalse(state.is_lords_day)
        self.assertFalse(state.is_stillpoint)

    def test_common_friday_governs_even_when_external_weekday_differs(self):
        # Host weekday is an observation coordinate, never a source of
        # Common Calendar authority; this intentional mismatch tests isolation.
        external_sunday = date(2026, 9, 20)
        civic_open = civil_dusk_utc(external_sunday, self.point)
        state = protected_time_state_for_common_date(
            civic_open,
            common_weekday="Friday",
            projection_date=external_sunday,
            location=self.point,
        )
        self.assertTrue(state.is_sabbath)
        self.assertTrue(state.is_stillpoint)
        self.assertEqual(state.named_day, "Saturday")

    def test_twilight_is_separate_from_sacred_sunset(self):
        friday = date(2026, 9, 18)
        sunset = apparent_sunset_utc(friday, self.point)
        dusk = civil_dusk_utc(friday, self.point)
        self.assertGreater((dusk - sunset).total_seconds(), 0)


if __name__ == "__main__":
    unittest.main()
