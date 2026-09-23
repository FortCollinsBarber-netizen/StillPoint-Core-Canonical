from __future__ import annotations

import unittest

from stillpoint.calendar_core.overlays import (
    ALL_OVERLAY_KINDS,
    OverlayRecord,
    grid_identity,
    inhabit_surface,
    overlay_policy_payload,
)
from stillpoint.calendar_core.runtime_surface import calendar_day_payload


class CalendarOverlayAuthorityTests(unittest.TestCase):
    def test_every_enacted_overlay_kind_has_zero_grid_authority(self):
        policy = overlay_policy_payload()
        self.assertEqual(
            policy["overlay_jurisdiction"]["rule"],
            "inhabit-the-surface-never-rewrite-the-surface",
        )
        self.assertFalse(policy["overlay_jurisdiction"]["grid_authority"])

        self.assertEqual(
            ALL_OVERLAY_KINDS,
            {
                "feast",
                "sabbath",
                "stillpoint",
                "season",
                "lunar",
                "jewish-calendar",
                "islamic-calendar",
                "seven-year",
                "forty-nine-year",
                "jubilee",
                "local-light",
            },
        )

    def test_all_overlay_families_can_inhabit_one_day_without_mutating_it(self):
        base = calendar_day_payload(2026, 344)  # December 10 / Thursday
        before = grid_identity(base)

        overlays = [
            OverlayRecord(
                kind="feast",
                id="feast-example",
                label="Sacred feast",
                source="enacted-feast-layer",
                data={"active": True},
            ),
            OverlayRecord(
                kind="sabbath",
                id="sabbath-state",
                label="Weekly Sabbath",
                source="weekly-protected-time",
                data={"active": False},
            ),
            OverlayRecord(
                kind="stillpoint",
                id="stillpoint-state",
                label="StillPoint",
                source="weekly-protected-time",
                data={"active": False},
            ),
            OverlayRecord(
                kind="season",
                id="season-witness",
                label="Season witness",
                source="enochic-and-observational-layer",
                data={"phase": 12},
            ),
            OverlayRecord(
                kind="lunar",
                id="lunar-witness",
                label="Lunar witness",
                source="astronomical-observation",
                data={"phase": "waxing", "illumination": 0.5},
            ),
            OverlayRecord(
                kind="jewish-calendar",
                id="jewish-calendar-witness",
                label="Jewish calendar overlay",
                source="qualified-external-calendar-adapter",
                data={"calendar_date": {"month": "Kislev", "day": 30}},
            ),
            OverlayRecord(
                kind="islamic-calendar",
                id="islamic-calendar-witness",
                label="Islamic calendar overlay",
                source="qualified-external-calendar-adapter",
                data={"calendar_date": {"month": "Rajab", "day": 1}},
            ),
            OverlayRecord(
                kind="seven-year",
                id="seven-year-position",
                label="Seven-year position",
                source="enacted-cycle-layer",
                data={"cycle_year": 1},
            ),
            OverlayRecord(
                kind="forty-nine-year",
                id="forty-nine-year-position",
                label="Forty-nine-year position",
                source="enacted-cycle-layer",
                data={"year": 1},
            ),
            OverlayRecord(
                kind="jubilee",
                id="jubilee-position",
                label="Jubilee position",
                source="enacted-cycle-layer",
                data={"cycle_year": 1, "is_jubilee_year": False},
            ),
            OverlayRecord(
                kind="local-light",
                id="local-light-witness",
                label="Local light",
                source="measured-or-computed-local-horizon",
                data={"event": "sunset", "observed": True},
            ),
        ]

        decorated = inhabit_surface(base, overlays)

        self.assertEqual(grid_identity(decorated), before)
        self.assertEqual(len(decorated["overlays"]), 11)
        for overlay in decorated["overlays"]:
            jurisdiction = overlay["jurisdiction"]
            self.assertFalse(jurisdiction["grid_authority"])
            self.assertFalse(jurisdiction["may_insert_days"])
            self.assertFalse(jurisdiction["may_delete_days"])
            self.assertFalse(jurisdiction["may_move_named_dates"])
            self.assertFalse(jurisdiction["may_change_weekday"])
            self.assertFalse(jurisdiction["may_change_year_opening"])
            self.assertFalse(jurisdiction["may_change_year_closing"])
            self.assertFalse(jurisdiction["may_change_year_length"])
            self.assertFalse(jurisdiction["may_create_leap_day"])
            self.assertFalse(jurisdiction["may_create_december_31"])

    def test_external_calendar_overlay_may_have_its_own_date_without_becoming_common_date(self):
        base = calendar_day_payload(2026, 1)
        jewish = OverlayRecord(
            kind="jewish-calendar",
            id="external-date",
            label="External date witness",
            source="qualified-external-calendar-adapter",
            data={
                "calendar_date": {
                    "year": 5786,
                    "month": "Tevet",
                    "day": 12,
                },
                "status": "witness-only",
            },
        )

        decorated = inhabit_surface(base, [jewish])

        self.assertEqual(
            decorated["common_date"],
            base["common_date"],
        )
        self.assertEqual(
            decorated["calendar_address"],
            "Y_2026-001",
        )
        self.assertEqual(
            decorated["overlays"][0]["authority_class"],
            "witness-overlay",
        )


if __name__ == "__main__":
    unittest.main()
