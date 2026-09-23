from __future__ import annotations

import unittest
from datetime import date

from stillpoint.calendar_core.calendar import ordinal_day
from stillpoint.calendar_core.overlays import (
    OverlayRecord,
    grid_identity,
    inhabit_surface,
)
from stillpoint.calendar_core.runtime_surface import calendar_day_payload
from stillpoint.calendar_core.witness_overlays import (
    ExternalCalendarWitness,
    witnesses_for_external_date,
)


class RhythmOverlayTests(unittest.TestCase):
    def test_jewish_witness_attaches_without_calendar_authority(self):
        day = calendar_day_payload(2026, ordinal_day(4, 1))
        overlays = {
            item["id"]: item
            for item in day["external_witness_overlays"]
        }

        self.assertEqual(day["common_date"]["weekday"], "Wednesday")
        self.assertIn("jewish-passover-2026", overlays)
        witness = overlays["jewish-passover-2026"]
        self.assertEqual(witness["begins_at"], "sunset")
        self.assertEqual(witness["authority"], "witness-only")
        self.assertFalse(witness["grid_authority"])
        self.assertEqual(witness["calendar_effect"], "none")

        # The Common Calendar's own Passover remains its separate sacred layer.
        canonical_passover = calendar_day_payload(2026, ordinal_day(1, 14))
        self.assertIn(
            "Passover",
            {item["name"] for item in canonical_passover["observances"]},
        )

    def test_islamic_witness_is_explicitly_sighting_qualified(self):
        day = calendar_day_payload(2026, ordinal_day(2, 17))
        witness = next(
            item
            for item in day["external_witness_overlays"]
            if item["id"] == "islamic-ramadan-begins-2026"
        )

        self.assertEqual(day["common_date"]["weekday"], "Tuesday")
        self.assertEqual(witness["begins_at"], "sunset")
        self.assertIn("sighting", witness["qualification"].lower())
        self.assertFalse(witness["grid_authority"])

    def test_seed_external_witnesses_do_not_repeat_as_calendar_law(self):
        seed = calendar_day_payload(2026, ordinal_day(9, 11))
        later = calendar_day_payload(2027, ordinal_day(9, 11))

        self.assertTrue(
            any(
                item["id"] == "jewish-rosh-hashanah-2026"
                for item in seed["external_witness_overlays"]
            )
        )
        self.assertEqual(later["external_witness_overlays"], [])
        self.assertEqual(
            seed["common_date"]["weekday"],
            later["common_date"]["weekday"],
        )

    def test_external_witness_catalog_can_be_filtered_by_calendar(self):
        jewish = witnesses_for_external_date(
            date(2026, 12, 4),
            calendars=["jewish"],
        )
        islamic = witnesses_for_external_date(
            date(2026, 12, 4),
            calendars=["islamic"],
        )

        self.assertEqual(
            [item.id for item in jewish],
            ["jewish-hanukkah-2026"],
        )
        self.assertEqual(islamic, ())

    def test_external_witness_payload_carries_governor_observe_receipt(self):
        day = calendar_day_payload(2026, ordinal_day(4, 1))
        witness = next(
            item
            for item in day["external_witness_overlays"]
            if item["id"] == "jewish-passover-2026"
        )

        receipt = witness["rhythm_governor"]
        self.assertEqual(receipt["authority"], "OBSERVE")
        self.assertEqual(receipt["decision"], "AUTHORIZED")
        self.assertFalse(receipt["surface_mutated"])

    def test_generic_overlay_policy_routes_canonical_and_witness_authority(self):
        base = calendar_day_payload(2026, ordinal_day(12, 10))
        before = grid_identity(base)
        decorated = inhabit_surface(
            base,
            [
                OverlayRecord(
                    kind="feast",
                    id="test-feast",
                    label="Test Feast",
                    source="test",
                    data={"note": "canonical overlay"},
                ),
                OverlayRecord(
                    kind="lunar",
                    id="test-lunar",
                    label="Test Lunar Witness",
                    source="test",
                    data={"phase": "full"},
                ),
            ],
        )

        self.assertEqual(grid_identity(decorated), before)
        by_id = {item["id"]: item for item in decorated["overlays"]}
        self.assertEqual(
            by_id["test-feast"]["rhythm_governor"]["authority"],
            "OVERLAY",
        )
        self.assertEqual(
            by_id["test-lunar"]["rhythm_governor"]["authority"],
            "OBSERVE",
        )
        for item in by_id.values():
            self.assertEqual(
                item["rhythm_governor"]["decision"],
                "AUTHORIZED",
            )
            self.assertFalse(
                item["rhythm_governor"]["surface_mutated"]
            )
            self.assertFalse(item["jurisdiction"]["grid_authority"])

    def test_external_witness_namespace_and_provenance_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "source_calendar"):
            ExternalCalendarWitness(
                id="bad-calendar",
                name="Bad Calendar",
                source_calendar="gregorian",
                external_date=date(2026, 1, 1),
                source_refs=("test",),
            )

        with self.assertRaisesRegex(ValueError, "source provenance"):
            ExternalCalendarWitness(
                id="missing-source",
                name="Missing Source",
                source_calendar="jewish",
                external_date=date(2026, 1, 1),
            )

        with self.assertRaisesRegex(ValueError, "unsupported external witness"):
            witnesses_for_external_date(
                date(2026, 1, 1),
                calendars=["gregorian"],
            )

    def test_seven_year_49_and_jubilee_layers_do_not_move_the_date(self):
        year7 = calendar_day_payload(2032, ordinal_day(7, 10))
        year49 = calendar_day_payload(2074, ordinal_day(7, 10))
        jubilee = calendar_day_payload(2075, ordinal_day(7, 10))

        self.assertTrue(year7["jubilee"]["seven_year"]["is_seventh_year"])
        self.assertEqual(year7["jubilee"]["seven_year"]["block"], 1)
        self.assertTrue(year49["jubilee"]["forty_nine"]["is_year_49"])
        self.assertTrue(jubilee["jubilee"]["forty_nine"]["completed"])
        self.assertTrue(jubilee["jubilee"]["is_jubilee_year"])
        self.assertTrue(jubilee["jubilee"]["is_jubilee_release_day"])

        coordinates = {
            (
                value["common_date"]["month"],
                value["common_date"]["day"],
                value["common_date"]["weekday"],
            )
            for value in (year7, year49, jubilee)
        }
        self.assertEqual(coordinates, {(7, 10, "Friday")})

    def test_seasonal_gate_is_overlay_state_not_grid_mutation(self):
        day = calendar_day_payload(2026, ordinal_day(10, 1))
        self.assertEqual(day["season"]["number"], 4)
        self.assertTrue(1 <= day["season"]["enoch_gate"] <= 6)
        self.assertIn(
            day["season"]["enoch_motion"],
            {
                "northward",
                "northward_to_turn",
                "northward_from_turn",
                "southward",
                "southward_to_turn",
                "southward_from_turn",
            },
        )
        self.assertEqual(day["map"]["year_days"], 364)
        self.assertFalse(day["map"]["december_31_exists"])


if __name__ == "__main__":
    unittest.main()
