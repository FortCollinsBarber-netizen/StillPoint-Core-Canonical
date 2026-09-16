"""Re-evaluation, re-entry, and release without erasure."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .claims import Claim, ClaimStatus
from .warrants import Warrant, WarrantStatus
from .evidence import EvidenceEvent


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strict_bool(value: Any, *, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    raise ValueError(f"{field_name} must be boolean/0/1, got {value!r}")


@dataclass
class ReevaluationTrigger:
    trigger_id: str
    prior_disposition: str
    prior_task_id: str | None = None
    prior_warrant_id: str | None = None
    prior_claim_ids: list[str] = field(default_factory=list)
    new_evidence_ids: list[str] = field(default_factory=list)
    reason: str = ""
    created_at: str = field(default_factory=_utcnow)
    new_evaluation_id: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.trigger_id:
            self.trigger_id = str(uuid4())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ReevaluationTrigger":
        return cls(
            trigger_id=raw["trigger_id"],
            prior_disposition=raw["prior_disposition"],
            prior_task_id=raw.get("prior_task_id"),
            prior_warrant_id=raw.get("prior_warrant_id"),
            prior_claim_ids=list(raw.get("prior_claim_ids") or []),
            new_evidence_ids=list(raw.get("new_evidence_ids") or []),
            reason=raw.get("reason", ""),
            created_at=raw.get("created_at") or _utcnow(),
            new_evaluation_id=raw.get("new_evaluation_id"),
            provenance=dict(raw.get("provenance") or {}),
        )


@dataclass
class ReleaseRecord:
    release_id: str
    subject: str
    prior_warrant_id: str | None = None
    prior_claim_ids: list[str] = field(default_factory=list)
    released_authority: str = ""
    reason: str = ""
    released_at: str = field(default_factory=_utcnow)
    retains_historical_record: bool = True
    restores_access: bool = False
    erases_consequences: bool = False
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.release_id:
            self.release_id = str(uuid4())
        if not self.retains_historical_record:
            raise ValueError("Release must retain historical record")
        if self.restores_access:
            raise ValueError("Release must not automatically restore access")
        if self.erases_consequences:
            raise ValueError("Release must not erase consequences")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ReleaseRecord":
        return cls(
            release_id=raw["release_id"],
            subject=raw["subject"],
            prior_warrant_id=raw.get("prior_warrant_id"),
            prior_claim_ids=list(raw.get("prior_claim_ids") or []),
            released_authority=raw.get("released_authority", ""),
            reason=raw.get("reason", ""),
            released_at=raw.get("released_at") or _utcnow(),
            retains_historical_record=_strict_bool(
                raw.get("retains_historical_record", True),
                field_name="retains_historical_record",
            ),
            restores_access=_strict_bool(
                raw.get("restores_access", False),
                field_name="restores_access",
            ),
            erases_consequences=_strict_bool(
                raw.get("erases_consequences", False),
                field_name="erases_consequences",
            ),
            provenance=dict(raw.get("provenance") or {}),
        )


def apply_new_evidence_to_claims(
    claims: list[Claim],
    evidence: EvidenceEvent,
    *,
    contradict_predicates: set[str] | None = None,
) -> list[Claim]:
    contradict_predicates = contradict_predicates or set()
    for claim in claims:
        if claim.subject != evidence.subject:
            continue
        if claim.status in (ClaimStatus.SUPERSEDED, ClaimStatus.WITHDRAWN):
            continue
        if claim.predicate in contradict_predicates or evidence.kind.value == "correction":
            claim.mark_review_required(f"new_evidence:{evidence.evidence_id}")
            if evidence.evidence_id not in [r.evidence_id for r in claim.evidence_refs]:
                from .claims import EvidenceRef
                claim.evidence_refs.append(
                    EvidenceRef(
                        evidence_id=evidence.evidence_id,
                        kind=evidence.kind.value,
                        note="ingress_after_claim",
                        observed_at=evidence.observed_at,
                        sha256=evidence.sha256,
                    )
                )
    return claims


def release_warrant(warrant: Warrant, release: ReleaseRecord) -> Warrant:
    if not release.prior_warrant_id:
        raise ValueError("release must identify prior_warrant_id")
    if release.prior_warrant_id != warrant.warrant_id:
        raise ValueError("release is bound to a different warrant")
    if release.subject != warrant.subject:
        raise ValueError("release subject does not match warrant subject")
    if warrant.status != WarrantStatus.ACTIVE:
        raise ValueError(f"only active warrant can be released, got {warrant.status.value}")
    warrant.complete()
    warrant.provenance["release_id"] = release.release_id
    warrant.provenance["release_reason"] = release.reason
    return warrant
