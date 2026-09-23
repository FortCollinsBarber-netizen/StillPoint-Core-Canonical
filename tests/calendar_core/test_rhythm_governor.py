from __future__ import annotations

import unittest

from stillpoint.calendar_core.governor import (
    ANCHOR_WEEKDAY,
    CANONICAL_TOTAL_DAYS,
    CANONICAL_WEEKS,
    CANONICAL_YEAR_DAYS,
    CalendarInvariantViolation,
    CanonicalDate,
    RHYTHM_GOVERNOR,
    RhythmAuthority,
    RhythmRequest,
    assert_canonical_surface,
    validate_transition,
)


class RhythmGovernorTests(unittest.TestCase):
    def test_locked_surface_self_validates(self):
        assert_canonical_surface()
        self.assertEqual(CANONICAL_YEAR_DAYS, 364)
        self.assertEqual(CANONICAL_WEEKS, 52)
        self.assertEqual(CANONICAL_TOTAL_DAYS, 18_200)
        self.assertEqual(ANCHOR_WEEKDAY, "Thursday")

    def test_anchor_dates_repeat_for_all_fifty_years(self):
        for year in range(2026, 2076):
            self.assertEqual(CanonicalDate(year, 1, 1).weekday, "Thursday")
            self.assertEqual(CanonicalDate(year, 12, 10).weekday, "Thursday")
            self.assertEqual(CanonicalDate(year, 12, 30).weekday, "Wednesday")

    def test_invalid_extra_dates_fail_closed(self):
        with self.assertRaises(ValueError):
            CanonicalDate(2028, 2, 29)
        with self.assertRaises(ValueError):
            CanonicalDate(2026, 12, 31)

    def test_december_30_transitions_directly_to_january_1(self):
        validate_transition(
            CanonicalDate(2026, 12, 30),
            CanonicalDate(2027, 1, 1),
        )
        with self.assertRaises(CalendarInvariantViolation):
            validate_transition(
                CanonicalDate(2026, 12, 30),
                CanonicalDate(2027, 1, 2),
            )

    def test_read_coordinate_observe_overlay_are_authorized(self):
        requests = [
            RhythmRequest(RhythmAuthority.READ, "calendar-os"),
            RhythmRequest(
                RhythmAuthority.COORDINATE,
                "appointments",
                canonical_date=CanonicalDate(2026, 12, 30),
                clock_time="23:59:59",
            ),
            RhythmRequest(
                RhythmAuthority.OBSERVE,
                "lunar-witness",
                annotation={"phase": "full"},
            ),
            RhythmRequest(
                RhythmAuthority.OVERLAY,
                "feast-engine",
                canonical_date=CanonicalDate(2026, 7, 10),
                annotation={"observance": "atonement"},
            ),
        ]
        for request in requests:
            decision = RHYTHM_GOVERNOR.authorize(request)
            self.assertTrue(decision.accepted, request)
            self.assertFalse(decision.surface_mutated)
            self.assertEqual(decision.authority, request.authority)

    def test_named_layers_may_inhabit_surface_but_never_rewrite_it(self):
        layers = [
            (RhythmAuthority.OVERLAY, "feasts"),
            (RhythmAuthority.OVERLAY, "sabbath"),
            (RhythmAuthority.OVERLAY, "stillpoint"),
            (RhythmAuthority.OVERLAY, "seasons"),
            (RhythmAuthority.OBSERVE, "lunar-witness"),
            (RhythmAuthority.OVERLAY, "jewish-overlay"),
            (RhythmAuthority.OVERLAY, "islamic-overlay"),
            (RhythmAuthority.OVERLAY, "seven-year-structure"),
            (RhythmAuthority.OVERLAY, "forty-nine-year-structure"),
            (RhythmAuthority.OVERLAY, "jubilee"),
            (RhythmAuthority.OBSERVE, "local-light"),
        ]
        canonical = CanonicalDate(2026, 12, 10)
        for authority, source in layers:
            decision = RHYTHM_GOVERNOR.authorize(
                RhythmRequest(
                    authority=authority,
                    source=source,
                    canonical_date=canonical,
                    annotation={"inhabits_surface": True},
                )
            )
            self.assertTrue(decision.accepted, source)
            self.assertFalse(decision.surface_mutated, source)
            self.assertEqual(decision.canonical_date, canonical)

            rejected = RHYTHM_GOVERNOR.authorize(
                RhythmRequest(
                    authority=authority,
                    source=source,
                    canonical_date=canonical,
                    annotation={"inhabits_surface": True},
                    attempts_grid_mutation=True,
                )
            )
            self.assertFalse(rejected.accepted, source)
            self.assertEqual(
                rejected.code,
                "CANONICAL_REOPENING_REQUIRED",
                source,
            )

    def test_there_is_no_runtime_calendar_mutation_authority(self):
        decision = RHYTHM_GOVERNOR.authorize(
            RhythmRequest(
                RhythmAuthority.OVERLAY,
                "external-adapter",
                attempts_grid_mutation=True,
            )
        )
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.authority, RhythmAuthority.REJECT)
        self.assertEqual(decision.code, "CANONICAL_REOPENING_REQUIRED")

    def test_dst_shift_is_rejected_but_24_hour_coordinate_is_retained(self):
        allowed = RHYTHM_GOVERNOR.authorize(
            RhythmRequest(
                RhythmAuthority.COORDINATE,
                "appointment-scheduler",
                canonical_date=CanonicalDate(2026, 3, 8),
                clock_time="15:30",
            )
        )
        self.assertTrue(allowed.accepted)

        rejected = RHYTHM_GOVERNOR.authorize(
            RhythmRequest(
                RhythmAuthority.COORDINATE,
                "external-clock",
                clock_time="15:30",
                dst_shift_seconds=3600,
            )
        )
        self.assertFalse(rejected.accepted)
        self.assertEqual(rejected.code, "DST_FORBIDDEN")

    def test_intercalation_and_reconciliation_are_rejected(self):
        for request, code in [
            (
                RhythmRequest(
                    RhythmAuthority.OBSERVE,
                    "astronomy",
                    intercalary_days=1,
                ),
                "INTERCALATION_FORBIDDEN",
            ),
            (
                RhythmRequest(
                    RhythmAuthority.OBSERVE,
                    "historical-reconciliation",
                    reconciliation_days=7,
                ),
                "RECONCILIATION_FORBIDDEN",
            ),
        ]:
            decision = RHYTHM_GOVERNOR.authorize(request)
            self.assertFalse(decision.accepted)
            self.assertEqual(decision.code, code)

    def test_observation_may_annotate_but_cannot_change_surface(self):
        decision = RHYTHM_GOVERNOR.authorize(
            RhythmRequest(
                RhythmAuthority.OBSERVE,
                "sunset-engine",
                canonical_date=CanonicalDate(2026, 9, 25),
                annotation={
                    "event": "sunset",
                    "host_iso_instant": "2026-09-25T18:52:00-07:00",
                },
            )
        )
        self.assertTrue(decision.accepted)
        self.assertFalse(decision.surface_mutated)
        self.assertEqual(decision.canonical_date.label, "2026-09-25")

    def test_foreign_calendar_translation_has_no_grid_authority(self):
        decision = RHYTHM_GOVERNOR.authorize(
            RhythmRequest(
                RhythmAuthority.OVERLAY,
                "gregorian-adapter",
                canonical_date=CanonicalDate(2027, 1, 1),
                annotation={"gregorian_label": "2026-12-31"},
            )
        )
        self.assertTrue(decision.accepted)
        self.assertEqual(decision.canonical_date.label, "2027-01-01")
        self.assertFalse(decision.surface_mutated)

    def test_surface_mutation_proposals_are_rejected(self):
        proposals = [
            RhythmRequest(
                RhythmAuthority.OVERLAY,
                "downstream",
                proposed_year_days=365,
            ),
            RhythmRequest(
                RhythmAuthority.OVERLAY,
                "downstream",
                proposed_weeks_per_year=53,
            ),
            RhythmRequest(
                RhythmAuthority.OVERLAY,
                "downstream",
                proposed_day001_weekday="Friday",
            ),
            RhythmRequest(
                RhythmAuthority.OVERLAY,
                "downstream",
                proposed_month_lengths=(
                    31, 29, 31, 30, 31, 30,
                    31, 31, 30, 31, 30, 29,
                ),
            ),
        ]
        for request in proposals:
            decision = RHYTHM_GOVERNOR.authorize(request)
            self.assertFalse(decision.accepted, request)
            self.assertEqual(decision.authority, RhythmAuthority.REJECT)

    def test_require_raises_on_jurisdiction_violation(self):
        with self.assertRaises(CalendarInvariantViolation) as raised:
            RHYTHM_GOVERNOR.require(
                RhythmRequest(
                    RhythmAuthority.OBSERVE,
                    "lunar-engine",
                    intercalary_days=1,
                )
            )
        self.assertEqual(raised.exception.code, "INTERCALATION_FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
