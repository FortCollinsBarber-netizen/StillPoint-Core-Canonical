"""Durable external-dispatch state machine.

The core safety rule is intentionally conservative:

    durable dispatch record -> consume one-use authority -> external adapter call

Once a real external dispatch crosses the durable boundary, the same ActionRequest
is never automatically dispatched again. If result persistence is interrupted or
the adapter raises after invocation, the state becomes uncertain and requires
explicit reconciliation. A confirmed-no-effect reconciliation still does not
resurrect the old warrant; retry requires a new ActionRequest / Warrant.

Null and dry-run adapters are probes, not external dispatches.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class DispatchState(str, Enum):
    DISPATCHING = "dispatching"
    COMPLETED = "completed"
    FAILED = "failed"
    UNCERTAIN = "uncertain"
    RECONCILED_EFFECT = "reconciled_effect"
    RECONCILED_NO_EFFECT = "reconciled_no_effect"


TERMINAL_DISPATCH_STATES = {
    DispatchState.COMPLETED.value,
    DispatchState.FAILED.value,
    DispatchState.RECONCILED_EFFECT.value,
    DispatchState.RECONCILED_NO_EFFECT.value,
}


class DispatchSafetyError(RuntimeError):
    pass


class DispatchAlreadyStarted(DispatchSafetyError):
    pass


class DispatchUncertain(DispatchSafetyError):
    pass


@dataclass(frozen=True)
class DispatchReceipt:
    action_id: str
    warrant_id: str
    adapter: str
    idempotency_key: str
    state: str
    started_at: str


def is_probe_adapter_name(name: str | None) -> bool:
    value = (name or "").strip()
    return value == "null" or value.startswith("dry_run")


def require_no_prior_real_dispatch(dispatch_row: dict[str, Any] | None) -> None:
    if not dispatch_row:
        return
    state = dispatch_row.get("state", "")
    if state in {"dispatching", "uncertain"}:
        raise DispatchUncertain(
            f"action already crossed external dispatch boundary with state={state}; "
            "reconciliation is required"
        )
    raise DispatchAlreadyStarted(
        f"action already has durable external dispatch state={state}; "
        "old authority is not reusable"
    )


def reconciliation_state(*, effect_occurred: bool) -> DispatchState:
    return (
        DispatchState.RECONCILED_EFFECT
        if effect_occurred
        else DispatchState.RECONCILED_NO_EFFECT
    )
