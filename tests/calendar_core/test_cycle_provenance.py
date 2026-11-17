from __future__ import annotations

import unittest

from stillpoint.calendar_core.calendar import ordinal_day
from stillpoint.calendar_core.long_cycles import JubileeConfiguration, compare_long_cycles
from stillpoint.calendar_core.runtime_surface import calendar_day_payload


class CycleProvenanceTests(unittest.TestCase):
    def test_legacy_default_is_identified_without_changing_its_result(self):
        payload = calendar_day_payload(2075, 1)
        self.assertTrue(payload["jubilee"]["is_jubilee_year"])
        configuration = payload["jubilee"]["configuration"]
        self.assertEqual(configuration["epoch_common_year"], 2026)
        self.assertEqual(configuration["rollover_rule"], "standalone-50")
        self.assertEqual(configuration["selection_source"], "legacy-publication-first-year-default")
        self.assertEqual(configuration["decision_status"], "rollover-reconciliation-unresolved")
        self.assertEqual(configuration["authority_scope"], "calculation-inputs-only")

    def test_explicit_2027_epoch_is_independent_of_the_civil_publication(self):
        original = calendar_day_payload(2075, 1)
        selected = calendar_day_payload(2075, 1,
            jubilee_configuration=JubileeConfiguration(epoch_common_year=2027))
        for key in ("calendar_address", "common_date", "common_civil_coordinate", "civil_window", "map", "publication"):
            self.assertEqual(original[key], selected[key])
        self.assertEqual(selected["jubilee"]["year"], 49)
        self.assertFalse(selected["jubilee"]["is_jubilee_year"])
        self.assertEqual(selected["jubilee"]["configuration"]["selection_source"], "explicit-call-configuration")

    def test_explicit_unconfigured_epoch_does_not_inherit_publication_year(self):
        payload = calendar_day_payload(2075, 1,
            jubilee_configuration=JubileeConfiguration(epoch_common_year=None))
        self.assertIsNone(payload["jubilee"]["cycle"])
        self.assertIsNone(payload["jubilee"]["year"])
        self.assertEqual(payload["jubilee"]["designation_status"], "unconfigured-epoch")
        self.assertIsNone(payload["long_cycle_comparison"]["models"])

    def test_before_epoch_is_identified(self):
        payload = calendar_day_payload(2026, 1,
            jubilee_configuration=JubileeConfiguration(epoch_common_year=2027))
        self.assertEqual(payload["jubilee"]["designation_status"], "before-epoch")
        self.assertEqual(payload["long_cycle_comparison"]["status"], "before-epoch")
        self.assertIsNone(payload["jubilee"]["year"])

    def test_explicit_inputs_are_validated_and_do_not_enable_an_unknown_rule(self):
        for value in (0, -1, True, 2027.0, "2027"):
            with self.subTest(epoch=value), self.assertRaises(ValueError):
                JubileeConfiguration(epoch_common_year=value)
        for value in (0, True):
            with self.subTest(cycle=value), self.assertRaises(ValueError):
                JubileeConfiguration(epoch_common_year=2027, epoch_cycle=value)
        with self.assertRaises(ValueError):
            JubileeConfiguration(epoch_common_year=2027, rollover_rule="overlap-49")
        with self.assertRaises(ValueError):
            calendar_day_payload(2026, 1, jubilee_configuration={"epoch_common_year": 2027})

    def test_counter_cycle_label_survives_runtime_comparison(self):
        payload = calendar_day_payload(2027, 1,
            jubilee_configuration=JubileeConfiguration(epoch_common_year=2027, epoch_cycle=3))
        self.assertEqual(payload["jubilee"]["cycle"], 3)
        comparison = payload["long_cycle_comparison"]["models"]["existing_standalone_fifty_year_counter"]
        self.assertEqual(comparison["cycle"], 3)

    def test_runtime_observance_keeps_scope_rule_and_unresolved_anchor(self):
        payload = calendar_day_payload(2026, ordinal_day(1, 25))
        item = next(item for item in payload["observances"] if item["id"] == "firstfruits")
        self.assertEqual(item["jurisdiction"], "sacred")
        self.assertIn("sabbath", item["rule"])
        self.assertIn("Leviticus 23:10-16", item["source_refs"])
        self.assertEqual(item["projection_status"], "legacy-placement-unreconciled-sacred-anchor")
        self.assertEqual(item["common_coordinate"], {"month": 1, "day": 25})
        self.assertNotIn("scriptural_coordinate", item)

    def test_new_year_observation_remains_a_scoped_common_observance(self):
        payload = calendar_day_payload(2026, 1)
        item = next(item for item in payload["observances"] if item["id"] == "new-year")
        self.assertEqual(item["jurisdiction"], "civic")
        self.assertEqual(item["projection_status"], "declared-common-observance")

    def test_release_label_does_not_claim_the_sacred_anchor_is_settled(self):
        payload = calendar_day_payload(2075, ordinal_day(7, 10))
        self.assertTrue(payload["jubilee"]["is_jubilee_release_day"])
        self.assertEqual(payload["jubilee"]["release_day_projection_status"],
                         "legacy-placement-unreconciled-sacred-anchor")
        self.assertFalse(payload["long_cycle_comparison"]["release_authority"])

    def test_epoch_choice_and_arithmetic_do_not_extend_the_publication(self):
        with self.assertRaises(ValueError):
            calendar_day_payload(2076, 1,
                jubilee_configuration=JubileeConfiguration(epoch_common_year=2027))
        comparison = compare_long_cycles(common_year=2076, epoch_common_year=2027)
        self.assertEqual(comparison["ordinal_year_from_epoch"], 50)
        models = comparison["models"]
        self.assertEqual(models["consecutive_forty_nine_year_blocks"]["year"], 1)
        self.assertTrue(models["existing_standalone_fifty_year_counter"]["is_jubilee_year"])
        self.assertEqual(models["consecutive_forty_nine_year_blocks"]["proclamation_rule"], "unresolved")
        self.assertFalse(comparison["grid_authority"])

    def test_missing_epoch_comparison_never_manufactures_positions(self):
        comparison = compare_long_cycles(common_year=2076, epoch_common_year=None)
        self.assertEqual(comparison["status"], "unconfigured-epoch")
        self.assertIsNone(comparison["models"])

    def test_first_combined_return_and_independent_fifty_are_distinct(self):
        # Enumerate year starts and weekly-course advancement independently of
        # the comparison function's LCM calculation.
        phase = 0
        first_return = None
        for elapsed in range(1, 295):
            phase = (phase + 52) % 24
            if phase == 0 and elapsed % 7 == 0 and elapsed % 49 == 0:
                first_return = elapsed
                break
        self.assertEqual(first_return, 294)
        comparison = compare_long_cycles(common_year=2027 + 294, epoch_common_year=2027)
        self.assertTrue(comparison["at_294_year_return_after_origin"])
        self.assertEqual(comparison["recurrence_years"], {
            "six_seven_forty_nine": 294, "with_independent_fifty": 7350})
        models = comparison["models"]
        self.assertEqual(models["six_year_priestly"]["course_phase_at_year_start_zero_based"], 0)
        self.assertFalse(models["existing_standalone_fifty_year_counter"]["is_jubilee_year"])
        self.assertEqual((7350 * 52) % 24, 0)
        self.assertEqual((7350 % 49, 7350 % 50), (0, 0))

    def test_a_forty_nine_year_boundary_does_not_reset_priestly_courses(self):
        comparison = compare_long_cycles(common_year=2076, epoch_common_year=2027)
        models = comparison["models"]
        self.assertEqual(models["six_year_priestly"]["course_phase_at_year_start_zero_based"], 4)
        self.assertTrue(models["consecutive_forty_nine_year_blocks"]["at_boundary_after_origin"])
        self.assertFalse(comparison["at_294_year_return_after_origin"])


if __name__ == "__main__":
    unittest.main()
