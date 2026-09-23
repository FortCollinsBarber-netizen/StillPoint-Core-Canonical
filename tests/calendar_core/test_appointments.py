import unittest
from datetime import date

from stillpoint.calendar_core.appointments import (
    AppointedTime,
    project_appointed_time,
)


class AppointedTimeTests(unittest.TestCase):
    def test_fixed_appointment_projects_downstream_of_law(self):
        atonement = AppointedTime(
            id="atonement",
            name="Day of Atonement",
            month=7,
            day=10,
        )
        occurrence = project_appointed_time(
            atonement,
            common_year=1,
            opening_civil_date=date(2026, 1, 1),
        )
        self.assertIsNotNone(occurrence)
        self.assertEqual(occurrence.calendar_state, "ORDINARY")
        self.assertEqual(occurrence.common_year, 1)
        self.assertEqual(
            (
                occurrence.closes_on_civil_date
                - occurrence.opens_on_civil_date
            ).days,
            1,
        )

    def test_outside_range_inherits_no_appointment(self):
        feast = AppointedTime(
            id="fixed",
            name="Fixed",
            month=1,
            day=1,
        )
        self.assertIsNone(
            project_appointed_time(
                feast,
                common_year=1,
                opening_civil_date=date(2026, 1, 1),
                calendar_state="OUTSIDE_RANGE",
            )
        )

    def test_invalid_fixed_date_fails_closed(self):
        with self.assertRaises(ValueError):
            AppointedTime(
                id="bad",
                name="Bad",
                month=12,
                day=31,
            )

    def test_fixed_date_weekday_is_year_label_independent(self):
        feast = AppointedTime(
            id="fixed",
            name="Fixed",
            month=12,
            day=25,
        )
        one = project_appointed_time(
            feast,
            common_year=1,
            opening_civil_date=date(2026, 1, 1),
        )
        later = project_appointed_time(
            feast,
            common_year=50,
            opening_civil_date=date(2026, 1, 1),
        )
        self.assertEqual(one.ordinal, later.ordinal)
        self.assertEqual(one.weekday, later.weekday)
        self.assertEqual(one.weekday, "Friday")

    def test_observance_projection_cannot_override_weekday_epoch(self):
        feast = AppointedTime(
            id="fixed",
            name="Fixed",
            month=1,
            day=1,
        )
        with self.assertRaises(TypeError):
            project_appointed_time(
                feast,
                common_year=1,
                opening_civil_date=date(2026, 1, 1),
                day001_weekday="Friday",
            )


if __name__ == "__main__":
    unittest.main()
