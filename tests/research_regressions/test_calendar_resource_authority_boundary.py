from __future__ import annotations

import pytest

from stillpoint.calendar_core.governor import (
    CanonicalDate,
    RhythmAuthority,
    RhythmGovernor,
    RhythmRequest,
)
from stillpoint.db import CompanyDB
from stillpoint.resource_custody import AcquiredResourceCustody, ResourceCustodyError


NOW = "2026-09-23T10:00:00+00:00"


@pytest.mark.parametrize(
    ("authority", "clock_time"),
    [
        (RhythmAuthority.OBSERVE, None),
        (RhythmAuthority.COORDINATE, "10:00:00"),
    ],
)
def test_calendar_information_cannot_manufacture_resource_activation_authority(
    tmp_path,
    authority,
    clock_time,
):
    governor = RhythmGovernor()
    decision = governor.require(
        RhythmRequest(
            authority=authority,
            source="common-calendar-runtime",
            canonical_date=CanonicalDate(2026, 9, 23),
            clock_time=clock_time,
            annotation={"local_light": "observed", "evidence_only": True},
        )
    )
    assert decision.accepted is True
    assert decision.surface_mutated is False

    db = CompanyDB(tmp_path / "company.sqlite")
    gate = AcquiredResourceCustody(db)
    gate.acquire(
        resource_id="calendar-informed-tool",
        owner_role="research",
        kind="provider_tool",
        discovered_capabilities=("web_research",),
        provenance={
            "calendar_decision": decision.code,
            "canonical_date": decision.canonical_date.label,
        },
        now_iso=NOW,
    )
    gate.resolve(
        "calendar-informed-tool",
        capabilities=("web_research",),
        authenticated_evidence={
            "calendar_decision": decision.code,
            "canonical_date": decision.canonical_date.label,
        },
        now_iso=NOW,
    )

    assert db.list_temporal_warrants() == []
    with pytest.raises(ResourceCustodyError) as exc:
        gate.activate(
            "calendar-informed-tool",
            warrant_id=decision.code,
            parent_capabilities=("web_research",),
            now_iso=NOW,
        )
    assert exc.value.code == "ACTIVATION_WARRANT_NOT_PERSISTED"
    assert gate.get("calendar-informed-tool").status == "resolved"
    db.close()


def test_resource_evidence_cannot_mutate_calendar_surface():
    governor = RhythmGovernor()
    rejected = governor.authorize(
        RhythmRequest(
            authority=RhythmAuthority.OVERLAY,
            source="acquired-resource-evidence",
            canonical_date=CanonicalDate(2026, 12, 30),
            annotation={"resource_status": "activated"},
            attempts_grid_mutation=True,
        )
    )
    assert rejected.accepted is False
    assert rejected.code == "CANONICAL_REOPENING_REQUIRED"
    assert rejected.surface_mutated is False
    assert rejected.canonical_date.weekday == "Wednesday"
