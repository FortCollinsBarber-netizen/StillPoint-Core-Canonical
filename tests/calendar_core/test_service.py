import unittest
from datetime import date, datetime, timedelta, timezone

from stillpoint.calendar_core.models import GeoPoint
from stillpoint.calendar_core.sunset import apparent_sunset_utc
from stillpoint.calendar_core.service import CalendarConfig, get_calendar_snapshot


class CalendarServiceTests(unittest.TestCase):
    def test_observation_zero_separates_calendar_identity_from_external_day(self):
        config = CalendarConfig(
            location=GeoPoint(40.3978, -105.0749, "LOVELAND_TEST"),
            local_zone="America/Denver",
            common_year=1,
            opening_civil_date=date(2026, 1, 1),
            common_standard_offset_seconds=-7 * 3600,
            reference_rule_version="immutable-364-v1",
            jubilee_epoch_common_year=1,
        )
        friday_sunset = apparent_sunset_utc(
            date(2026, 9, 18),
            config.location,
        )
        snap = get_calendar_snapshot(
            friday_sunset + timedelta(seconds=1),
            config=config,
        )

        self.assertEqual(snap.common_date.ordinal, 261)
        self.assertEqual(snap.common_date.weekday, "Friday")
        self.assertEqual(snap.named_day, "Saturday")
        self.assertTrue(snap.sabbath_active)
        self.assertTrue(snap.stillpoint_active)
        self.assertEqual(snap.annual_phase, 9)
        self.assertEqual(snap.solar_gate, 1)
        self.assertEqual(snap.jubilee.cycle_year, 1)
        self.assertEqual(
            snap.reference_rule_version,
            "immutable-364-v1",
        )

    def test_translation_config_cannot_supply_calendar_weekday_identity(self):
        with self.assertRaises(TypeError):
            CalendarConfig(
                location=GeoPoint(40.3978, -105.0749, "LOVELAND_TEST"),
                local_zone="America/Denver",
                common_year=1,
                opening_civil_date=date(2026, 1, 1),
                common_standard_offset_seconds=-7 * 3600,
                day001_weekday="Friday",
            )


if __name__ == "__main__":
    unittest.main()
