# StillPoint Core Patch 002 — Mandatory Action Warrant Gate

Base: Patch 001 commit `a71d16b52d96312e0f05d7d14ceea628d6661bba`.

This patch makes temporal authority part of the actual consequential-action runtime.

## Behavior
- An `ActionRequest` without a bound Warrant is never dispatch-permitted.
- Explicit CEO approval issues a finite one-use Warrant rather than acting as a magic bypass.
- The Warrant is bound to exact action class, task subject, target, action scope, artifact IDs/versions/hashes, authority revision, approval ID, and expiration.
- `execute_action()` revalidates the Warrant immediately before dispatch.
- One warrant use is durably reserved before adapter execution.
- Adapter exceptions mark the reservation `uncertain`; the runtime must not silently retry that action.
- Completion consumes the Warrant by moving it to `completed`.

## Migration
Migration 007 adds action-to-warrant binding and durable warrant-consumption records. Migrations 001-006 remain unchanged.

## Apply
1. Copy this bundle into the Patch-001 repository root.
2. Run `python apply_patch_002.py .`
3. Run the focused test: `python -m unittest tests.test_mandatory_action_warrant -v`
4. Run the complete existing test suite.
5. Repair only genuine integration mismatches; do not weaken the fail-closed rules.

The patcher intentionally aborts when expected source anchors are not exact.

## Next
Patch 003 should formalize the complete dispatch state machine and crash/retry reconciliation, including the case where an external effect may have occurred but an `ActionResult` was never persisted.
