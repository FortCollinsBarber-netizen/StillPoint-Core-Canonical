"""Standing delegation model for StillPoint Autonomous Operations.

A standing delegation is reusable policy standing, not an execution warrant.
It may establish that a role is eligible to request a bounded execution warrant
for an in-scope action while continuation conditions remain satisfied.

This module intentionally contains no warrant-minting method.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from stillpoint.temporal.envelope import (
    ClaimEnvelope,
    ContinuationCondition,
    StandingState,
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_time(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception as exc:
        raise ValueError(f"invalid delegation time: {value!r}") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("delegation times must be timezone-aware")
    return dt.astimezone(timezone.utc)


def _nonempty(values: list[str] | tuple[str, ...]) -> list[str]:
    return [str(v).strip() for v in values if str(v).strip()]


class DelegationStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"
    REVIEW_REQUIRED = "review_required"


class DelegationStanding(str, Enum):
    CURRENT = "current"
    FORMER = "former"
    REVIEW_REQUIRED = "review_required"


@dataclass(frozen=True)
class DelegationAssessment:
    standing: DelegationStanding
    action_in_scope: bool
    failed_conditions: list[str] = field(default_factory=list)
    supporting_envelopes: list[str] = field(default_factory=list)
    note: str = ""

    @property
    def eligible_for_warrant_consideration(self) -> bool:
        """Eligibility is not authorization and never implies a warrant exists."""
        return self.standing is DelegationStanding.CURRENT and self.action_in_scope


@dataclass(frozen=True)
class StandingDelegation:
    delegation_id: str
    delegate_role: str
    issuer: str
    policy_basis: str
    purpose: str
    claim_envelope_ids: list[str]
    allowed_action_types: list[str]
    continuation_conditions: list[ContinuationCondition]
    execution_conditions: list[ContinuationCondition]
    exclusions: list[str]
    release_conditions: list[str]
    valid_from: str
    review_by: str
    status: DelegationStatus = DelegationStatus.ACTIVE
    supersedes_delegation_id: str | None = None
    created_at: str = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if not self.delegation_id:
            object.__setattr__(self, "delegation_id", str(uuid4()))
        if isinstance(self.status, str):
            object.__setattr__(self, "status", DelegationStatus(self.status))
        for name, value in (
            ("delegate_role", self.delegate_role),
            ("issuer", self.issuer),
            ("policy_basis", self.policy_basis),
            ("purpose", self.purpose),
        ):
            if not str(value).strip():
                raise ValueError(f"{name} required")

        envelopes = _nonempty(self.claim_envelope_ids)
        actions = _nonempty(self.allowed_action_types)
        exclusions = _nonempty(self.exclusions)
        releases = _nonempty(self.release_conditions)
        object.__setattr__(self, "claim_envelope_ids", envelopes)
        object.__setattr__(self, "allowed_action_types", actions)
        object.__setattr__(self, "exclusions", exclusions)
        object.__setattr__(self, "release_conditions", releases)

        wildcard = {"*", "all", "any", "unrestricted"}
        if wildcard.intersection({a.lower() for a in actions}):
            raise ValueError("standing delegation cannot use unrestricted action wildcard")
        missing: list[str] = []
        if not envelopes:
            missing.append("claim_envelope_ids")
        if not actions:
            missing.append("allowed_action_types")
        if not self.continuation_conditions:
            missing.append("continuation_conditions")
        if not self.execution_conditions:
            missing.append("execution_conditions")
        if not releases:
            missing.append("release_conditions")
        if missing:
            raise ValueError("standing delegation missing: " + ", ".join(missing))

        start = _parse_time(self.valid_from)
        review = _parse_time(self.review_by)
        if review <= start:
            raise ValueError("review_by must be after valid_from")

    def assess(
        self,
        *,
        now_iso: str,
        continuation_facts: dict[str, Any],
        action_type: str,
        execution_facts: dict[str, Any],
        envelopes: dict[str, ClaimEnvelope],
        envelope_facts: dict[str, dict[str, Any]] | None = None,
        proposed_use_by_envelope: dict[str, str] | None = None,
    ) -> DelegationAssessment:
        envelope_facts = envelope_facts or {}
        proposed_use_by_envelope = proposed_use_by_envelope or {}

        if self.status in {
            DelegationStatus.REVOKED,
            DelegationStatus.EXPIRED,
            DelegationStatus.SUPERSEDED,
        }:
            return DelegationAssessment(
                standing=DelegationStanding.FORMER,
                action_in_scope=False,
                note="delegation is former and cannot govern present action",
            )
        if self.status in {DelegationStatus.SUSPENDED, DelegationStatus.REVIEW_REQUIRED}:
            return DelegationAssessment(
                standing=DelegationStanding.REVIEW_REQUIRED,
                action_in_scope=False,
                note="delegation requires review before reuse",
            )

        now = _parse_time(now_iso)
        if now < _parse_time(self.valid_from):
            return DelegationAssessment(
                standing=DelegationStanding.REVIEW_REQUIRED,
                action_in_scope=False,
                failed_conditions=["delegation_not_yet_valid"],
            )
        if now >= _parse_time(self.review_by):
            return DelegationAssessment(
                standing=DelegationStanding.REVIEW_REQUIRED,
                action_in_scope=False,
                failed_conditions=["delegation_review_due"],
                note="review boundary does not renew itself",
            )

        failed: list[str] = []
        supporting: list[str] = []
        for envelope_id in self.claim_envelope_ids:
            envelope = envelopes.get(envelope_id)
            if not envelope:
                failed.append(f"missing_envelope:{envelope_id}")
                continue
            envelope_assessment = envelope.assess_continuation(
                facts=envelope_facts.get(envelope_id, continuation_facts),
                proposed_use=proposed_use_by_envelope.get(envelope_id, ""),
            )
            if envelope_assessment.state is not StandingState.CURRENT:
                failed.append(f"envelope_not_current:{envelope_id}")
            else:
                supporting.append(envelope_id)

        for condition in self.continuation_conditions:
            ok, reason = condition.evaluate(continuation_facts)
            if not ok:
                failed.append(reason or condition.key)

        action_in_scope = action_type in self.allowed_action_types
        if not action_in_scope:
            failed.append("action_type_out_of_scope")
        for condition in self.execution_conditions:
            ok, reason = condition.evaluate(execution_facts)
            if not ok:
                failed.append(reason or condition.key)

        if failed:
            return DelegationAssessment(
                standing=DelegationStanding.REVIEW_REQUIRED,
                action_in_scope=action_in_scope,
                failed_conditions=failed,
                supporting_envelopes=supporting,
                note="standing or scope failed; no warrant may be inferred",
            )

        return DelegationAssessment(
            standing=DelegationStanding.CURRENT,
            action_in_scope=True,
            supporting_envelopes=supporting,
            note="eligible for separate execution-warrant consideration only",
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["continuation_conditions"] = [c.to_dict() for c in self.continuation_conditions]
        data["execution_conditions"] = [c.to_dict() for c in self.execution_conditions]
        return data
