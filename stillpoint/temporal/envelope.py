"""Claim Envelope / Continuing Evidence contract.

This layer does not grant authority. It preserves the conditions under which a
claim may be considered operationally relevant, records whether the claim has
already been used to alter its environment, and keeps memory distinct from
reauthorization.

A ClaimEnvelope can establish that a proposed use is in scope and that stated
continuation conditions remain satisfied. It cannot mint, extend, or replace a
StillPoint warrant. Consequential action still requires the ordinary action /
warrant gate.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _nonempty(values: list[str] | tuple[str, ...]) -> list[str]:
    return [str(v).strip() for v in values if str(v).strip()]


def _resolve_fact(facts: dict[str, Any], key: str) -> tuple[bool, Any]:
    current: Any = facts
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return True, current


class EnvelopeStatus(str, Enum):
    ACTIVE = "active"
    HISTORICAL = "historical"
    SUPERSEDED = "superseded"
    REVIEW_REQUIRED = "review_required"


class StandingState(str, Enum):
    CURRENT = "current"
    FORMER = "former"
    REVIEW_REQUIRED = "review_required"


class ConditionOperator(str, Enum):
    EQ = "eq"
    NEQ = "neq"
    IN = "in"
    NOT_IN = "not_in"
    PRESENT = "present"
    ABSENT = "absent"
    LTE = "lte"
    GTE = "gte"


class ClaimUseKind(str, Enum):
    INFORMATIONAL = "informational"
    OPERATIONAL = "operational"
    INTERVENTION = "intervention"


class EvidenceEnvironment(str, Enum):
    PRE_INTERVENTION = "pre_intervention"
    POST_INTERVENTION = "post_intervention"
    MIXED = "mixed"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class EpistemicReach:
    available_sources: list[str] = field(default_factory=list)
    unavailable_sources: list[str] = field(default_factory=list)
    observed_variables: list[str] = field(default_factory=list)
    inferred_variables: list[str] = field(default_factory=list)
    model_boundaries: list[str] = field(default_factory=list)
    blind_spots: list[str] = field(default_factory=list)

    def has_stated_reach(self) -> bool:
        return any(
            _nonempty(values)
            for values in (
                self.available_sources,
                self.unavailable_sources,
                self.observed_variables,
                self.inferred_variables,
                self.model_boundaries,
                self.blind_spots,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContinuationCondition:
    key: str
    operator: ConditionOperator = ConditionOperator.EQ
    expected: Any = None
    note: str = ""

    def __post_init__(self) -> None:
        if not str(self.key).strip():
            raise ValueError("continuation condition key required")
        if isinstance(self.operator, str):
            object.__setattr__(self, "operator", ConditionOperator(self.operator))
        if self.operator in {ConditionOperator.IN, ConditionOperator.NOT_IN} and not isinstance(
            self.expected, (list, tuple, set, frozenset)
        ):
            raise ValueError(f"{self.operator.value} requires a collection expected value")

    def evaluate(self, facts: dict[str, Any]) -> tuple[bool, str]:
        present, actual = _resolve_fact(facts, self.key)
        op = self.operator
        if op is ConditionOperator.PRESENT:
            return present, "" if present else f"missing:{self.key}"
        if op is ConditionOperator.ABSENT:
            return (not present), "" if not present else f"unexpected_present:{self.key}"
        if not present:
            return False, f"missing:{self.key}"
        try:
            if op is ConditionOperator.EQ:
                ok = actual == self.expected
            elif op is ConditionOperator.NEQ:
                ok = actual != self.expected
            elif op is ConditionOperator.IN:
                ok = actual in self.expected
            elif op is ConditionOperator.NOT_IN:
                ok = actual not in self.expected
            elif op is ConditionOperator.LTE:
                ok = actual <= self.expected
            elif op is ConditionOperator.GTE:
                ok = actual >= self.expected
            else:
                ok = False
        except Exception:
            return False, f"unevaluable:{self.key}"
        return ok, "" if ok else f"condition_failed:{self.key}:{op.value}"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["operator"] = self.operator.value
        return data


@dataclass(frozen=True)
class MemoryPolicy:
    purposes: list[str] = field(default_factory=lambda: ["history", "accountability"])
    retain_until: str | None = None
    operational_reauthorization: bool = False

    def __post_init__(self) -> None:
        if self.operational_reauthorization:
            raise ValueError("memory cannot itself reauthorize operational authority")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContinuationAssessment:
    state: StandingState
    failed_conditions: list[str] = field(default_factory=list)
    use_in_scope: bool = False
    note: str = ""

    @property
    def continuation_satisfied(self) -> bool:
        return self.state is StandingState.CURRENT and not self.failed_conditions


@dataclass(frozen=True)
class ClaimEnvelope:
    envelope_id: str
    claim_id: str
    domain: str
    purpose: str
    epistemic_reach: EpistemicReach
    permitted_uses: list[str] = field(default_factory=list)
    prohibited_uses: list[str] = field(default_factory=list)
    continuation_conditions: list[ContinuationCondition] = field(default_factory=list)
    correction_routes: list[str] = field(default_factory=list)
    release_conditions: list[str] = field(default_factory=list)
    reentry_requirements: list[str] = field(default_factory=list)
    memory_policy: MemoryPolicy = field(default_factory=MemoryPolicy)
    operational: bool = False
    status: EnvelopeStatus = EnvelopeStatus.ACTIVE
    supersedes_envelope_id: str | None = None
    created_at: str = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if not self.envelope_id:
            object.__setattr__(self, "envelope_id", str(uuid4()))
        if not str(self.claim_id).strip():
            raise ValueError("claim_id required")
        if not str(self.domain).strip():
            raise ValueError("domain required")
        if not str(self.purpose).strip():
            raise ValueError("purpose required")
        if isinstance(self.status, str):
            object.__setattr__(self, "status", EnvelopeStatus(self.status))

        permitted = _nonempty(self.permitted_uses)
        prohibited = _nonempty(self.prohibited_uses)
        object.__setattr__(self, "permitted_uses", permitted)
        object.__setattr__(self, "prohibited_uses", prohibited)

        wildcard = {"*", "all", "any", "unrestricted"}
        if self.operational and wildcard.intersection({u.lower() for u in permitted}):
            raise ValueError("operational envelope cannot use unrestricted permitted-use wildcard")
        overlap = set(permitted).intersection(prohibited)
        if overlap:
            raise ValueError(f"use cannot be both permitted and prohibited: {sorted(overlap)}")

        if self.operational:
            missing: list[str] = []
            if not self.epistemic_reach.has_stated_reach():
                missing.append("epistemic_reach")
            if not permitted:
                missing.append("permitted_uses")
            if not self.continuation_conditions:
                missing.append("continuation_conditions")
            if not _nonempty(self.correction_routes):
                missing.append("correction_routes")
            if not _nonempty(self.release_conditions):
                missing.append("release_conditions")
            if not _nonempty(self.reentry_requirements):
                missing.append("reentry_requirements")
            if missing:
                raise ValueError("operational envelope missing: " + ", ".join(missing))

    def use_is_in_scope(self, proposed_use: str) -> bool:
        """Return scope membership only. This is never an authorization decision."""
        proposed = str(proposed_use).strip()
        if not proposed or proposed in self.prohibited_uses:
            return False
        return proposed in self.permitted_uses

    def assess_continuation(
        self,
        *,
        facts: dict[str, Any],
        proposed_use: str = "",
    ) -> ContinuationAssessment:
        """Assess current standing conditions without granting action authority."""
        in_scope = self.use_is_in_scope(proposed_use) if proposed_use else True
        if self.status in {EnvelopeStatus.HISTORICAL, EnvelopeStatus.SUPERSEDED}:
            return ContinuationAssessment(
                state=StandingState.FORMER,
                use_in_scope=in_scope,
                note="historically preserved; presently non-governing",
            )
        if self.status is EnvelopeStatus.REVIEW_REQUIRED:
            return ContinuationAssessment(
                state=StandingState.REVIEW_REQUIRED,
                use_in_scope=in_scope,
                note="envelope already requires review",
            )

        failed: list[str] = []
        for condition in self.continuation_conditions:
            ok, reason = condition.evaluate(facts)
            if not ok:
                failed.append(reason or condition.key)
        if failed or not in_scope:
            if not in_scope:
                failed.append("use_out_of_scope")
            return ContinuationAssessment(
                state=StandingState.REVIEW_REQUIRED,
                failed_conditions=failed,
                use_in_scope=in_scope,
                note="continuation must be re-established before operational reliance",
            )
        return ContinuationAssessment(
            state=StandingState.CURRENT,
            use_in_scope=in_scope,
            note="conditions satisfied; separate warrant still required for consequential action",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "envelope_id": self.envelope_id,
            "claim_id": self.claim_id,
            "domain": self.domain,
            "purpose": self.purpose,
            "epistemic_reach": self.epistemic_reach.to_dict(),
            "permitted_uses": list(self.permitted_uses),
            "prohibited_uses": list(self.prohibited_uses),
            "continuation_conditions": [c.to_dict() for c in self.continuation_conditions],
            "correction_routes": list(self.correction_routes),
            "release_conditions": list(self.release_conditions),
            "reentry_requirements": list(self.reentry_requirements),
            "memory_policy": self.memory_policy.to_dict(),
            "operational": self.operational,
            "status": self.status.value,
            "supersedes_envelope_id": self.supersedes_envelope_id,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ClaimUseEvent:
    use_id: str
    claim_id: str
    envelope_id: str
    use_kind: ClaimUseKind
    actor: str
    purpose: str
    occurred_at: str = field(default_factory=_utcnow)
    warrant_id: str | None = None
    action_id: str | None = None
    intervention_effects: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.use_id:
            object.__setattr__(self, "use_id", str(uuid4()))
        if isinstance(self.use_kind, str):
            object.__setattr__(self, "use_kind", ClaimUseKind(self.use_kind))
        if not self.claim_id or not self.envelope_id or not str(self.actor).strip():
            raise ValueError("claim_id, envelope_id, and actor required")
        if self.use_kind in {ClaimUseKind.OPERATIONAL, ClaimUseKind.INTERVENTION}:
            if not self.warrant_id or not self.action_id:
                raise ValueError("operational claim use requires bound warrant_id and action_id")
        if self.use_kind is ClaimUseKind.INTERVENTION and not _nonempty(self.intervention_effects):
            raise ValueError("intervention use requires stated intervention effects")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["use_kind"] = self.use_kind.value
        return data


@dataclass(frozen=True)
class EvidenceContext:
    evidence_id: str
    environment: EvidenceEnvironment
    prior_use_ids: list[str] = field(default_factory=list)
    system_influence: list[str] = field(default_factory=list)
    recorded_at: str = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if not self.evidence_id:
            raise ValueError("evidence_id required")
        if isinstance(self.environment, str):
            object.__setattr__(self, "environment", EvidenceEnvironment(self.environment))
        if self.environment in {EvidenceEnvironment.POST_INTERVENTION, EvidenceEnvironment.MIXED}:
            if not _nonempty(self.prior_use_ids):
                raise ValueError("post-intervention or mixed evidence requires prior_use_ids")

    @property
    def independent_of_prior_system_use(self) -> bool | None:
        if self.environment is EvidenceEnvironment.PRE_INTERVENTION:
            return True
        if self.environment in {EvidenceEnvironment.POST_INTERVENTION, EvidenceEnvironment.MIXED}:
            return False
        return None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["environment"] = self.environment.value
        return data
