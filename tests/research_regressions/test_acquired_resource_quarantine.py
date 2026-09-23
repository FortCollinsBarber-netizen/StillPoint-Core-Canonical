from __future__ import annotations

import sqlite3

import pytest

from stillpoint.db import CompanyDB
from stillpoint.resource_custody import AcquiredResourceCustody, ResourceCustodyError
from stillpoint.temporal.warrants import Warrant


NOW = "2026-09-23T10:00:00+00:00"


def activation_warrant(
    db: CompanyDB,
    resource_id: str,
    *,
    capabilities=("web_research",),
    valid_to="2026-09-23T11:00:00+00:00",
) -> Warrant:
    warrant = Warrant(
        warrant_id=f"activate-{resource_id}",
        domain="resource",
        action_class="activate_resource",
        subject=resource_id,
        issuer="CEO:Robert Emmanuel LaDay",
        policy_basis="explicit acquired-resource activation",
        valid_from="2026-09-23T09:00:00+00:00",
        valid_to=valid_to,
        scope={"capabilities": list(capabilities)},
    )
    db.add_temporal_warrant(warrant)
    return warrant


def custody(tmp_path):
    db = CompanyDB(tmp_path / "company.sqlite")
    return db, AcquiredResourceCustody(db)


def test_acquisition_is_durable_but_cannot_self_activate_after_restart(tmp_path):
    db, gate = custody(tmp_path)
    gate.acquire(
        resource_id="tool-1",
        owner_role="builder",
        kind="provider_tool",
        discovered_capabilities=("web_research",),
        provenance={"source": "runtime acquisition"},
        now_iso=NOW,
    )
    assert gate.get("tool-1").status == "quarantined"
    assert db.list_temporal_warrants() == []
    db.close()

    reopened = CompanyDB(tmp_path / "company.sqlite")
    restored = AcquiredResourceCustody(reopened)
    assert restored.get("tool-1").status == "quarantined"
    with pytest.raises(ResourceCustodyError) as exc:
        restored.assert_usable("tool-1", "web_research", now_iso=NOW)
    assert exc.value.code == "RESOURCE_NOT_ACTIVE"
    reopened.close()


def test_resolution_is_evidence_not_authority_and_cannot_widen_parent_scope(tmp_path):
    db, gate = custody(tmp_path)
    gate.acquire(
        resource_id="tool-2",
        owner_role="research",
        kind="provider_tool",
        discovered_capabilities=("web_research",),
        now_iso=NOW,
    )
    resolved = gate.resolve(
        "tool-2",
        capabilities=("web_research", "send_email"),
        authenticated_evidence={"attestation": "capability inspection"},
        now_iso=NOW,
    )
    assert resolved.status == "resolved"
    assert "send_email" in resolved.resolved_capabilities

    warrant = activation_warrant(
        db,
        "tool-2",
        capabilities=("web_research", "send_email"),
    )
    with pytest.raises(ResourceCustodyError) as exc:
        gate.activate(
            "tool-2",
            warrant_id=warrant.warrant_id,
            parent_capabilities=("web_research",),
            now_iso=NOW,
        )
    assert exc.value.code == "PARENT_SCOPE_WIDENING"
    assert gate.get("tool-2").status == "resolved"
    db.close()


def test_activation_requires_separately_persisted_current_warrant(tmp_path):
    db, gate = custody(tmp_path)
    gate.acquire(
        resource_id="tool-3",
        owner_role="research",
        kind="provider_tool",
        discovered_capabilities=("web_research",),
        now_iso=NOW,
    )
    gate.resolve(
        "tool-3",
        capabilities=("web_research",),
        authenticated_evidence="signed inspection",
        now_iso=NOW,
    )

    with pytest.raises(ResourceCustodyError) as exc:
        gate.activate(
            "tool-3",
            warrant_id="not-issued",
            parent_capabilities=("web_research",),
            now_iso=NOW,
        )
    assert exc.value.code == "ACTIVATION_WARRANT_NOT_PERSISTED"

    warrant = activation_warrant(db, "tool-3")
    active = gate.activate(
        "tool-3",
        warrant_id=warrant.warrant_id,
        parent_capabilities=("web_research",),
        now_iso=NOW,
    )
    assert active.status == "activated"
    assert active.authorized_capabilities == ("web_research",)
    db.close()


def test_use_revalidates_activation_warrant_at_point_of_use(tmp_path):
    db, gate = custody(tmp_path)
    gate.acquire(
        resource_id="tool-4",
        owner_role="research",
        kind="provider_tool",
        discovered_capabilities=("web_research",),
        now_iso=NOW,
    )
    gate.resolve(
        "tool-4",
        capabilities=("web_research",),
        authenticated_evidence="signed inspection",
        now_iso=NOW,
    )
    warrant = activation_warrant(
        db,
        "tool-4",
        valid_to="2026-09-23T10:10:00+00:00",
    )
    gate.activate(
        "tool-4",
        warrant_id=warrant.warrant_id,
        parent_capabilities=("web_research",),
        now_iso=NOW,
    )

    gate.assert_usable(
        "tool-4",
        "web_research",
        now_iso="2026-09-23T10:09:59+00:00",
    )
    with pytest.raises(ResourceCustodyError) as exc:
        gate.assert_usable(
            "tool-4",
            "web_research",
            now_iso="2026-09-23T10:10:00+00:00",
        )
    assert exc.value.code == "ACTIVATION_WARRANT_INVALID"
    db.close()


def test_one_shot_use_is_consumed_before_effect_and_restart_cannot_replay(tmp_path):
    db, gate = custody(tmp_path)
    gate.acquire(
        resource_id="credential-1",
        owner_role="signal",
        kind="credential",
        discovered_capabilities=("send_email",),
        one_shot=True,
        now_iso=NOW,
    )
    gate.resolve(
        "credential-1",
        capabilities=("send_email",),
        authenticated_evidence={"verified_by": "credential resolver"},
        now_iso=NOW,
    )
    warrant = activation_warrant(
        db,
        "credential-1",
        capabilities=("send_email",),
    )
    gate.activate(
        "credential-1",
        warrant_id=warrant.warrant_id,
        parent_capabilities=("send_email",),
        now_iso=NOW,
    )
    spent = gate.reserve_one_shot_use(
        "credential-1",
        "send_email",
        now_iso="2026-09-23T10:01:00+00:00",
    )
    assert spent.status == "consumed"
    db.close()

    reopened = CompanyDB(tmp_path / "company.sqlite")
    restored = AcquiredResourceCustody(reopened)
    assert restored.get("credential-1").status == "consumed"
    with pytest.raises(ResourceCustodyError) as exc:
        restored.reserve_one_shot_use(
            "credential-1",
            "send_email",
            now_iso="2026-09-23T10:02:00+00:00",
        )
    assert exc.value.code == "RESOURCE_NOT_ACTIVE"
    with pytest.raises(ResourceCustodyError) as exc:
        restored.activate(
            "credential-1",
            warrant_id=warrant.warrant_id,
            parent_capabilities=("send_email",),
            now_iso="2026-09-23T10:02:00+00:00",
        )
    assert exc.value.code == "RESOURCE_NOT_RESOLVED"
    reopened.close()


def test_terminal_state_and_custody_events_are_database_enforced(tmp_path):
    db, gate = custody(tmp_path)
    gate.acquire(
        resource_id="credential-2",
        owner_role="signal",
        kind="credential",
        discovered_capabilities=("send_email",),
        one_shot=True,
        now_iso=NOW,
    )
    gate.resolve(
        "credential-2",
        capabilities=("send_email",),
        authenticated_evidence="verified",
        now_iso=NOW,
    )
    warrant = activation_warrant(
        db,
        "credential-2",
        capabilities=("send_email",),
    )
    gate.activate(
        "credential-2",
        warrant_id=warrant.warrant_id,
        parent_capabilities=("send_email",),
        now_iso=NOW,
    )
    gate.reserve_one_shot_use("credential-2", "send_email", now_iso=NOW)

    conn = db._connection()
    with pytest.raises(sqlite3.DatabaseError, match="terminal acquired resource cannot revive"):
        conn.execute(
            "UPDATE acquired_resources SET status='activated' WHERE resource_id='credential-2'"
        )
    conn.rollback()

    event = gate.list_events("credential-2")[0]
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        conn.execute(
            "UPDATE acquired_resource_events SET event_type='blocked' WHERE event_id=?",
            (event["event_id"],),
        )
    conn.rollback()
    db.close()


def test_schema_advances_to_acquired_resource_custody(tmp_path):
    db = CompanyDB(tmp_path / "company.sqlite")
    assert db.schema_version == 24
    db.close()
