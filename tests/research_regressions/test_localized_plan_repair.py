from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

import pytest

from stillpoint.db import CompanyDB
from stillpoint.models import WorkPlan
from stillpoint.providers.mock import MockProvider
from stillpoint.registry import AgentRegistry
from stillpoint.runtime import CompanyRuntime


ROOT = Path(__file__).resolve().parents[2]


def runtime(tmp: Path) -> CompanyRuntime:
    return CompanyRuntime(
        root=tmp,
        db=CompanyDB(tmp / "db.sqlite"),
        registry=AgentRegistry(ROOT / "config" / "agents.json"),
        provider=MockProvider(),
        default_model="mock",
        smart_routing=False,
    )


def staged_plan(authority_revision: str) -> WorkPlan:
    return WorkPlan(
        primary="builder",
        contributors=["research", "ledger"],
        contributor_specs=[
            {
                "id": "research",
                "reason": "research prefix",
                "capabilities": ["web_research"],
                "before": "next_contributor",
            },
            {
                "id": "ledger",
                "reason": "analysis prefix",
                "capabilities": [],
                "before": "primary",
            },
        ],
        expected_artifact="code",
        authority_revision=authority_revision,
    )


def test_localized_repair_preserves_two_completed_steps_and_artifact_hashes():
    with tempfile.TemporaryDirectory() as td:
        rt = runtime(Path(td))
        goal = "Research, analyze, then build the implementation."
        task_id = rt.db.create_task(goal, "runtime")
        old_plan = staged_plan("authority-old")
        rt.db.set_plan(task_id, old_plan.to_dict())

        research_run = rt.db.add_run(
            task_id,
            "research",
            "contribution",
            "RESEARCH-V1",
            input_summary="fp:old-research",
            stage_key=f"{task_id}:fixture:research",
        )
        ledger_run = rt.db.add_run(
            task_id,
            "ledger",
            "contribution",
            "LEDGER-V1",
            input_summary="fp:old-ledger",
            stage_key=f"{task_id}:fixture:ledger",
        )
        rt.db.add_run(
            task_id,
            "builder",
            "primary",
            "BUILD-V1",
            input_summary="fp:old-build",
            stage_key=f"{task_id}:fixture:builder",
        )

        research_hash = hashlib.sha256(b"research artifact").hexdigest()
        ledger_hash = hashlib.sha256(b"ledger artifact").hexdigest()
        rt.db.add_artifact(
            task_id=task_id,
            project="runtime",
            kind="research_notes",
            name="research.json",
            sha256=research_hash,
            produced_by_run_id=research_run,
            phase="contribution",
        )
        rt.db.add_artifact(
            task_id=task_id,
            project="runtime",
            kind="ledger_analysis",
            name="analysis.json",
            sha256=ledger_hash,
            produced_by_run_id=ledger_run,
            phase="contribution",
        )
        rt.db.update_task(task_id, status="failed", error="correction arrived at step 3")

        new_plan = staged_plan("authority-new")
        rt.planner.plan = lambda effective: (new_plan, "", False, "deterministic")

        before_artifacts = {
            (a["id"], a["sha256"])
            for a in rt.db.list_artifacts(task_id)
            if a["produced_by_run_id"] in {research_run, ledger_run}
        }
        result = rt.repair(
            task_id,
            "Correct only the build step; the research and analysis are still valid.",
            preserve_completed_steps=2,
        )

        assert result.status.value == "completed"
        runs = rt.db.list_runs(task_id)
        assert len([r for r in runs if r["phase"] == "contribution" and r["agent_id"] == "research"]) == 1
        assert len([r for r in runs if r["phase"] == "contribution" and r["agent_id"] == "ledger"]) == 1
        assert len([r for r in runs if r["phase"] == "primary" and r["agent_id"] == "builder"]) == 2

        after_artifacts = {
            (a["id"], a["sha256"])
            for a in rt.db.list_artifacts(task_id)
            if a["produced_by_run_id"] in {research_run, ledger_run}
        }
        assert after_artifacts == before_artifacts
        assert {sha for _, sha in after_artifacts} == {research_hash, ledger_hash}

        repair_rows = [r for r in runs if r["phase"] == "repair_boundary"]
        assert len(repair_rows) == 1
        receipt = json.loads(repair_rows[0]["output"])
        assert [p["run_id"] for p in receipt["preserved_steps"]] == [research_run, ledger_run]
        assert receipt["prior_authority_revision"] == "authority-old"
        assert receipt["new_authority_revision"] == "authority-new"
        rt.db.close()


def test_repair_invalidates_old_approved_action_and_revokes_unspent_warrant():
    with tempfile.TemporaryDirectory() as td:
        rt = runtime(Path(td))
        outcome = rt.submit("Send the email to Jane.")
        assert outcome.status.value == "waiting_approval"
        task_id = outcome.task_id

        rt.approve(task_id)
        action = rt.db.list_action_requests(task_id)[0]
        warrant_id = action["warrant_id"]
        assert warrant_id
        assert rt.db.get_temporal_warrant(warrant_id).status.value == "active"

        replacement = WorkPlan(
            primary="builder",
            expected_artifact="code",
            restricted_actions=[],
            external_action_intent="none",
            authority_revision="repair-no-send",
        )
        rt.planner.plan = lambda effective: (replacement, "", False, "deterministic")

        repaired = rt.repair(
            task_id,
            "Cancel the send. Keep the work internal.",
            preserve_completed_steps=0,
        )
        assert repaired.status.value == "completed"

        old_action = rt.db.get_action_request(action["id"])
        assert old_action["status"] == "stale"
        assert rt.db.get_temporal_warrant(warrant_id).status.value == "revoked"
        assert rt.db.get_action_dispatch(action["id"]) is None

        receipt = json.loads(
            [r for r in rt.db.list_runs(task_id) if r["phase"] == "repair_boundary"][0]["output"]
        )
        assert action["id"] in receipt["invalidated_action_ids"]
        rt.db.close()


def test_repair_refuses_to_preserve_stage_whose_identity_changed():
    with tempfile.TemporaryDirectory() as td:
        rt = runtime(Path(td))
        task_id = rt.db.create_task("Research then build.", "runtime")
        old_plan = WorkPlan(
            primary="builder",
            contributors=["research"],
            contributor_specs=[
                {
                    "id": "research",
                    "reason": "research prefix",
                    "capabilities": ["web_research"],
                    "before": "primary",
                }
            ],
            authority_revision="old",
        )
        rt.db.set_plan(task_id, old_plan.to_dict())
        rt.db.add_run(
            task_id,
            "research",
            "contribution",
            "DONE",
            input_summary="fp:old",
            stage_key=f"{task_id}:fixture:research",
        )
        rt.db.update_task(task_id, status="failed", error="repair requested")

        changed = WorkPlan(
            primary="builder",
            contributors=["ledger"],
            contributor_specs=[
                {
                    "id": "ledger",
                    "reason": "changed prefix",
                    "capabilities": [],
                    "before": "primary",
                }
            ],
            authority_revision="new",
        )
        rt.planner.plan = lambda effective: (changed, "", False, "deterministic")

        with pytest.raises(RuntimeError, match="preserved stage identity"):
            rt.repair(task_id, "Change the plan.", preserve_completed_steps=1)

        assert len([r for r in rt.db.list_runs(task_id) if r["phase"] == "contribution"]) == 1
        rt.db.close()
