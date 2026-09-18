import datetime as dt
import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "generate_common_calendar_v33.py"
SPEC = importlib.util.spec_from_file_location("common_calendar_v33", MODULE_PATH)
assert SPEC and SPEC.loader
v33 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v33)


class CommonCalendarV33Tests(unittest.TestCase):
    latitude = 40.4
    longitude = -105.1

    def test_loveland_sunset_preserves_next_utc_day_rollover(self):
        sunset = v33.sunset_utc(
            dt.date(2026, 9, 18),
            self.latitude,
            self.longitude,
        )
        self.assertEqual(sunset.date(), dt.date(2026, 9, 19))
        self.assertGreaterEqual(sunset.hour, 0)
        self.assertLess(sunset.hour, 3)

    def test_ordinary_year_is_always_364_and_reconciliation_is_separate(self):
        opening = dt.date(2027, 3, 17)
        immediate = opening + dt.timedelta(days=364)
        next_equinox = v33.sunset_utc(immediate, self.latitude, self.longitude)

        doc = v33.generate(
            latitude=self.latitude,
            longitude=self.longitude,
            first_year_label=2027,
            first_opening=opening,
            count=1,
            ephemerides={2028: next_equinox},
            ephemeris_source="test",
            ephemeris_sha256="0" * 64,
            publish_coordinates=False,
        )

        row = doc["years"][0]
        self.assertEqual(row["reconciliationDaysAfterCompletion"], 0)
        self.assertNotIn("yearLength", row)
        self.assertEqual(doc["snapOperator"], "NearestLegalReentry")
        self.assertNotIn("latitude", doc["referencePoint"])
        self.assertNotIn("longitude", doc["referencePoint"])
        v33.validate_output(doc)

    def test_delayed_reentry_is_seven_transition_days_not_a_371_day_year(self):
        opening = dt.date(2027, 3, 17)
        delayed = opening + dt.timedelta(days=371)
        next_equinox = v33.sunset_utc(delayed, self.latitude, self.longitude)

        doc = v33.generate(
            latitude=self.latitude,
            longitude=self.longitude,
            first_year_label=2027,
            first_opening=opening,
            count=1,
            ephemerides={2028: next_equinox},
            ephemeris_source="test",
            ephemeris_sha256="1" * 64,
            publish_coordinates=False,
        )

        row = doc["years"][0]
        self.assertEqual(row["reconciliationDaysAfterCompletion"], 7)
        self.assertNotIn("yearLength", row)
        v33.validate_output(doc)

    def test_two_published_openings_obey_declared_transition(self):
        opening = dt.date(2027, 3, 17)
        immediate_2028 = opening + dt.timedelta(days=364)
        immediate_2029 = immediate_2028 + dt.timedelta(days=364)

        doc = v33.generate(
            latitude=self.latitude,
            longitude=self.longitude,
            first_year_label=2027,
            first_opening=opening,
            count=2,
            ephemerides={
                2028: v33.sunset_utc(immediate_2028, self.latitude, self.longitude),
                2029: v33.sunset_utc(immediate_2029, self.latitude, self.longitude),
            },
            ephemeris_source="test",
            ephemeris_sha256="2" * 64,
            publish_coordinates=False,
        )

        first = dt.date.fromisoformat(doc["years"][0]["openingCivilDate"])
        second = dt.date.fromisoformat(doc["years"][1]["openingCivilDate"])
        self.assertEqual((second - first).days, 364)
        v33.validate_output(doc)


if __name__ == "__main__":
    unittest.main()
