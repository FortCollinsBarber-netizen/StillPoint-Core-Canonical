from __future__ import annotations

import unittest

from stillpoint.dispatch import (
    DispatchAlreadyStarted,
    DispatchState,
    DispatchUncertain,
    is_probe_adapter_name,
    reconciliation_state,
    require_no_prior_real_dispatch,
)


class DispatchStateMachineTests(unittest.TestCase):
    def test_probe_detection(self):
        self.assertTrue(is_probe_adapter_name("null"))
        self.assertTrue(is_probe_adapter_name("dry_run"))
        self.assertTrue(is_probe_adapter_name("dry_run:test"))
        self.assertFalse(is_probe_adapter_name("smtp"))

    def test_dispatching_blocks_retry_as_uncertain(self):
        with self.assertRaises(DispatchUncertain):
            require_no_prior_real_dispatch({"state": "dispatching"})

    def test_uncertain_blocks_retry(self):
        with self.assertRaises(DispatchUncertain):
            require_no_prior_real_dispatch({"state": "uncertain"})

    def test_terminal_states_never_reuse_old_authority(self):
        for state in (
            "completed",
            "failed",
            "reconciled_effect",
            "reconciled_no_effect",
        ):
            with self.subTest(state=state):
                with self.assertRaises(DispatchAlreadyStarted):
                    require_no_prior_real_dispatch({"state": state})

    def test_no_dispatch_row_is_dispatchable(self):
        require_no_prior_real_dispatch(None)

    def test_reconciliation_state(self):
        self.assertEqual(
            reconciliation_state(effect_occurred=True),
            DispatchState.RECONCILED_EFFECT,
        )
        self.assertEqual(
            reconciliation_state(effect_occurred=False),
            DispatchState.RECONCILED_NO_EFFECT,
        )


if __name__ == "__main__":
    unittest.main()
