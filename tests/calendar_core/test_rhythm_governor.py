from __future__ import annotations

import unittest

from stillpoint.calendar_core.governor import (
    GOVERNING_RULE,
    INHABITANT_LAYER_POLICY,
    CalendarAuthority,
    CalendarAuthorityViolation,
    RhythmGovernor,
)


class RhythmGovernorTests(unittest.TestCase):
    def setUp(self):
        self.governor = RhythmGovernor()

    def test_authority_vocabulary_deliberately_has_no_mutation_permission(self):
        self.assertEqual(
            {item.value for item in CalendarAuthority},
            {"READ", "COORDINATE", "OBSERVE", "OVERLAY", "REJECT"},
        )
        self.assertNotIn("MUTATE", {item.name for item in CalendarAuthority})
        self.assertNotIn(
            "MUTATE_CALENDAR",
            {item.value for item in CalendarAuthority},
        )

    def test_surface_integrity_proves_locked_fifty_year_geometry(self):
        state = self.governor.assert_surface_integrity()

        self.assertEqual(state["governing_rule"], GOVERNING_RULE)
        self.assertEqual(state["template_year"], 2026)
        self.assertEqual(state["year_days"], 364)
        self.assertEqual(state["weeks_per_year"], 52)
        self.assertEqual(state["year_count"], 50)
        self.assertEqual(state["total_dates"], 18_200)
        self.assertEqual(state["first_year"], 2026)
        self.assertEqual(state["last_year"], 2075)
        self.assertEqual(state["day001_weekday"], "Thursday")
        self.assertFalse(state["december_31_exists"])
        self.assertFalse(state["february_29_exists"])
        self.assertFalse(state["ordinary_mutation_authority_exists"])

    def test_forbidden_dates_fail_closed(self):
        with self.assertRaises(ValueError):
            self.governor.validate_date(2026, 12, 31)
        with self.assertRaises(ValueError):
            self.governor.validate_date(2028, 2, 29)

    def test_december_30_transitions_directly_to_january_1(self):
        closing = self.governor.validate_date(2026, 12, 30)
        opening = self.governor.next_date(2026, 12, 30)

        self.assertEqual(
            (closing.month, closing.day, closing.weekday),
            (12, 30, "Wednesday"),
        )
        self.assertEqual(
            (opening.year, opening.month, opening.day, opening.weekday),
            (2027, 1, 1, "Thursday"),
        )

    def test_permanent_weekday_anchors_hold_through_year_50(self):
        expected = {
            (1, 1): "Thursday",
            (12, 10): "Thursday",
            (12, 24): "Thursday",
            (12, 25): "Friday",
            (12, 30): "Wednesday",
        }
        for year in range(2026, 2076):
            for (month, day), weekday in expected.items():
                self.assertEqual(
                    self.governor.weekday_for(year, month, day),
                    weekday,
                    (year, month, day),
                )

    def test_read_returns_calendar_core_without_acquiring_mutation_authority(self):
        day = self.governor.read_day(2026, 344)

        self.assertEqual(day["schema"], "stillpoint.calendar-day.v1")
        self.assertEqual(day["authority"], "read-only-calendar-law")
        self.assertEqual(day["calendar_address"], "Y_2026-344")
        self.assertEqual(
            (
                day["common_date"]["month"],
                day["common_date"]["day"],
                day["common_date"]["weekday"],
            ),
            (12, 10, "Thursday"),
        )

    def test_24_hour_coordination_is_allowed_without_dst(self):
        decision = self.governor.require(
            CalendarAuthority.COORDINATE,
            payload={
                "appointment": {
                    "date": "Y_2026-266",
                    "time": "15:30:00",
                    "clock": "24-hour",
                },
                "dst_enabled": False,
            },
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.authority, CalendarAuthority.COORDINATE)

    def test_dst_shift_is_rejected(self):
        decision = self.governor.decide(
            CalendarAuthority.COORDINATE,
            payload={"dst_shift_seconds": 3600},
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.authority, CalendarAuthority.REJECT)
        self.assertTrue(decision.canonical_reopening_required)

        with self.assertRaises(CalendarAuthorityViolation):
            self.governor.require(
                CalendarAuthority.COORDINATE,
                payload={"daylight_saving_enabled": True},
            )

    def test_observation_can_report_sunset_without_rewriting_surface(self):
        before = self.governor.surface_digest
        envelope = self.governor.annotate(
            CalendarAuthority.OBSERVE,
            year=2026,
            month=9,
            day=23,
            payload={
                "event": "sunset",
                "instant_utc": "2026-09-24T00:53:00+00:00",
                "source": "local-solar-observation",
            },
        )
        after = self.governor.surface_digest

        self.assertEqual(envelope["authority"], "OBSERVE")
        self.assertEqual(envelope["calendar_address"], "Y_2026-266")
        self.assertFalse(envelope["grid_mutated"])
        self.assertEqual(before, after)

    def test_jewish_islamic_lunar_and_feast_overlays_are_informative_only(self):
        examples = (
            {"system": "Jewish", "observance": "example"},
            {"system": "Islamic", "observance": "example"},
            {"system": "lunar", "phase": "new moon"},
            {"system": "feast", "observance": "Passover"},
            {"system": "seasonal", "gate": 4},
            {"system": "Jubilee", "cycle_year": 50},
        )
        baseline = self.governor.surface_digest

        for payload in examples:
            envelope = self.governor.annotate(
                CalendarAuthority.OVERLAY,
                year=2026,
                month=1,
                day=1,
                payload=payload,
            )
            self.assertEqual(envelope["authority"], "OVERLAY")
            self.assertFalse(envelope["grid_mutated"])
            self.assertEqual(envelope["surface_digest"], baseline)

        self.assertEqual(self.governor.surface_digest, baseline)

    def test_every_inhabitant_layer_can_live_on_surface_without_owning_it(self):
        expected = {
            "feasts": "OVERLAY",
            "sabbath": "OVERLAY",
            "stillpoint": "OVERLAY",
            "seasons": "OVERLAY",
            "lunar-witness": "OBSERVE",
            "jewish-overlay": "OVERLAY",
            "islamic-overlay": "OVERLAY",
            "seven-year-cycle": "OVERLAY",
            "forty-nine-year-cycle": "OVERLAY",
            "jubilee": "OVERLAY",
            "local-light": "OBSERVE",
        }
        self.assertEqual(
            {key: value.value for key, value in INHABITANT_LAYER_POLICY.items()},
            expected,
        )

        baseline = self.governor.surface_digest
        for layer, authority in expected.items():
            envelope = self.governor.inhabit(
                layer,
                year=2026,
                month=9,
                day=23,
                payload={"example": layer},
            )
            self.assertEqual(envelope["layer_authority"], authority)
            self.assertEqual(envelope["surface_authority"], "none")
            self.assertFalse(envelope["grid_mutated"])
            self.assertEqual(envelope["surface_digest"], baseline)

        self.assertEqual(self.governor.surface_digest, baseline)

    def test_inhabitant_layer_cannot_smuggle_a_surface_rewrite(self):
        decision = self.governor.decide(
            CalendarAuthority.OVERLAY,
            payload={
                "layer": "jubilee",
                "layer_payload": {
                    "surface_patch": {"insert_day": "December 31"},
                },
            },
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.authority, CalendarAuthority.REJECT)
        self.assertTrue(decision.canonical_reopening_required)

    def test_observation_does_not_gain_authority_by_claiming_a_correction(self):
        decision = self.governor.decide(
            CalendarAuthority.OBSERVE,
            payload={"event": "astronomical-discrepancy"},
            proposed_surface_change={"insert_day": "December 31"},
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.authority, CalendarAuthority.REJECT)
        self.assertTrue(decision.canonical_reopening_required)

    def test_external_calendar_adapter_may_translate_but_not_patch(self):
        translated = self.governor.decide(
            CalendarAuthority.OVERLAY,
            payload={
                "external_system": "Gregorian",
                "external_label": "2027-01-01",
                "canonical_address": "Y_2027-001",
            },
        )
        self.assertTrue(translated.allowed)

        patch = self.governor.decide(
            CalendarAuthority.OVERLAY,
            payload={"external_system": "Gregorian"},
            proposed_surface_change={
                "calendar_patch": {"December": 31},
            },
        )
        self.assertFalse(patch.allowed)
        self.assertEqual(patch.authority, CalendarAuthority.REJECT)

    def test_unknown_mutation_action_is_rejected_not_inferred(self):
        decision = self.governor.decide(
            "MUTATE_CALENDAR",
            payload={"reason": "astronomical correction"},
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.authority, CalendarAuthority.REJECT)
        self.assertTrue(decision.canonical_reopening_required)


if __name__ == "__main__":
    unittest.main()
