from __future__ import annotations

import json
from pathlib import Path

import pytest

from stillpoint.adapters.base import NotAuthorized
from stillpoint.adapters.registry import ActionAdapterRegistry
from stillpoint.contracts.models import ActionResult
from stillpoint.db import CompanyDB
from stillpoint.models import WorkPlan
from stillpoint.providers.mock import MockProvider
from stillpoint.registry import AgentRegistry
from stillpoint.runtime import CompanyRuntime


ROOT = Path(__file__).resolve().parents[1]


class SpySendAdapter:
    name = "spy_send"
    action_types = ("send_email",)

    def __init__(self):
        self.executions = 0

    def can_execute(self, request):
        return True

    def execute(self, request):
        self.executions += 1
        return ActionResult(
            action_id=request.action_id,
            status="succeeded",
            evidence=[],
            adapter=self.name,
            external_id="spy",
        )


def runtime(tmp_path: Path) -> CompanyRuntime:
    return CompanyRuntime(
        root=tmp_path,
        db=CompanyDB(tmp_path / "db.sqlite"),
        registry=AgentRegistry(ROOT / "config" / "agents.json"),
        provider=MockProvider(),
        default_model="mock",
        smart_routing=False,
    )


def approved_send(rt: CompanyRuntime):
    outcome = rt.submit("Send the email to Jane.")
    assert outcome.status.value == "waiting_approval"
    action = rt.db.list_action_requests(outcome.task_id)[0]
    rt.approve(outcome.task_id)
    action = rt.db.get_action_request(action["id"])
    assert action["status"] == "ready_for_action"
    return outcome.task_id, action


def current_plan(rt: CompanyRuntime, task_id: str) -> WorkPlan:
    task = rt.db.get_task(task_id)
    return WorkPlan.from_dict(json.loads(task["plan_json"]))


def test_changed_authority_revision_blocks_before_adapter_execution(tmp_path):
    rt = runtime(tmp_path)
    task_id, action = approved_send(rt)
    adapter = SpySendAdapter()
    registry = ActionAdapterRegistry([adapter])

    plan = current_plan(rt, task_id)
    plan.authority_revision = "revoked-by-repair"
    rt.db.set_plan(task_id, plan.to_dict())

    with pytest.raises(NotAuthorized, match="authority revision"):
        rt.execute_action(action["id"], registry)

    assert adapter.executions == 0
    assert rt.db.get_action_request(action["id"])["status"] == "stale"
    assert rt.db.get_action_dispatch(action["id"]) is None
    rt.db.close()


def test_removed_external_intent_invalidates_old_approved_action(tmp_path):
    rt = runtime(tmp_path)
    task_id, action = approved_send(rt)
    adapter = SpySendAdapter()
    registry = ActionAdapterRegistry([adapter])

    plan = current_plan(rt, task_id)
    # Keep the revision deliberately unchanged: current intent is an independent
    # invocation-time condition and cannot be inferred from an old warrant.
    plan.restricted_actions = []
    plan.external_action_intent = "none"
    plan.approval_required = False
    rt.db.set_plan(task_id, plan.to_dict())

    with pytest.raises(NotAuthorized, match="no longer present"):
        rt.execute_action(action["id"], registry)

    assert adapter.executions == 0
    assert rt.db.get_action_request(action["id"])["status"] == "stale"
    rt.db.close()


def test_stale_status_is_not_dispatchable_even_with_valid_old_warrant(tmp_path):
    rt = runtime(tmp_path)
    _, action = approved_send(rt)
    adapter = SpySendAdapter()
    registry = ActionAdapterRegistry([adapter])

    rt.db.mark_action_stale(action["id"])

    with pytest.raises(NotAuthorized, match="status=stale"):
        rt.execute_action(action["id"], registry)

    assert adapter.executions == 0
    assert rt.db.get_action_dispatch(action["id"]) is None
    rt.db.close()


def test_db_boundary_rechecks_plan_after_reservation_before_external_effect(tmp_path):
    rt = runtime(tmp_path)
    task_id, row = approved_send(rt)
    req = rt._request_from_row(row)
    warrant = rt.db.get_temporal_warrant(req.warrant_id)

    # Establish that the original warrant is valid and reserve it while the
    # original plan is still current.
    rt.db.reserve_warrant_for_action(
        action_id=req.action_id,
        warrant_id=req.warrant_id,
        authority_revision=req.authority_revision,
        approval_id=req.approval_id,
        artifact_hashes=[ref.sha256 for ref in req.artifact_refs],
    )

    plan = current_plan(rt, task_id)
    plan.authority_revision = "changed-after-reservation"
    rt.db.set_plan(task_id, plan.to_dict())

    with pytest.raises(RuntimeError, match="authority revision is no longer current"):
        rt.db.begin_external_dispatch(
            action_id=req.action_id,
            warrant_id=warrant.warrant_id,
            adapter="spy_send",
            idempotency_key=req.idempotency_key,
            authority_revision=req.authority_revision,
            approval_id=req.approval_id,
            artifact_hashes=[ref.sha256 for ref in req.artifact_refs],
        )

    assert rt.db.get_action_dispatch(req.action_id) is None
    # No external boundary was crossed; the one-use warrant remains active.
    assert rt.db.get_temporal_warrant(req.warrant_id).status == "active"
    rt.db.close()
