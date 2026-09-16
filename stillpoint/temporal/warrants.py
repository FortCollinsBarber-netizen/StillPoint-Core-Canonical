"""Temporal warrants: explicit, finite authority to act.

Warrant is not claim. Claim is not warrant.
Scope(action) <= Scope(warrant).
Malformed temporal or serialized state fails closed.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_boundary(value: str | None, *, required: bool = False) -> datetime | None:
    if not value:
        if required:
            raise ValueError("required temporal boundary missing")
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception as exc:
        raise ValueError(f"invalid temporal boundary: {value!r}") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"temporal boundary must be timezone-aware: {value!r}")
    return dt.astimezone(timezone.utc)


class WarrantStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    COMPLETED = "completed"
    SUPERSEDED = "superseded"
    REVIEW_REQUIRED = "review_required"


@dataclass(frozen=True)
class WarrantScope:
    domain: str
    action_class: str
    subjects: tuple[str, ...] = ()
    targets: tuple[str, ...] = ()
    max_actions: int | None = None
    cross_domain_claim_domains: tuple[str, ...] = ()


@dataclass
class Warrant:
    warrant_id: str
    domain: str
    action_class: str
    subject: str
    target: str = ""
    claim_ids: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    issuer: str = ""
    policy_basis: str = ""
    issued_at: str = field(default_factory=_utcnow)
    valid_from: str = field(default_factory=_utcnow)
    valid_to: str | None = None
    status: WarrantStatus = WarrantStatus.ACTIVE
    scope: dict[str, Any] = field(default_factory=dict)
    completion_condition: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utcnow)
    updated_at: str = field(default_factory=_utcnow)
    superseded_by: str | None = None
    revoked_reason: str = ""
    completed_at: str | None = None

    def __post_init__(self) -> None:
        if not self.warrant_id:
            self.warrant_id = str(uuid4())

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value if isinstance(self.status, WarrantStatus) else self.status
        return d

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Warrant":
        raw_status = raw.get("status")
        if isinstance(raw_status, WarrantStatus):
            status = raw_status
        elif raw_status in WarrantStatus._value2member_map_:
            status = WarrantStatus(raw_status)
        else:
            status = WarrantStatus.REVIEW_REQUIRED

        provenance = dict(raw.get("provenance") or {})
        if raw_status not in WarrantStatus._value2member_map_ and not isinstance(raw_status, WarrantStatus):
            provenance["deserialization_warning"] = f"unknown_warrant_status:{raw_status!r}"

        return cls(
            warrant_id=raw["warrant_id"],
            domain=raw["domain"],
            action_class=raw["action_class"],
            subject=raw["subject"],
            target=raw.get("target", ""),
            claim_ids=list(raw.get("claim_ids") or []),
            evidence_ids=list(raw.get("evidence_ids") or []),
            issuer=raw.get("issuer", ""),
            policy_basis=raw.get("policy_basis", ""),
            issued_at=raw.get("issued_at") or _utcnow(),
            valid_from=raw.get("valid_from") or _utcnow(),
            valid_to=raw.get("valid_to"),
            status=status,
            scope=dict(raw.get("scope") or {}),
            completion_condition=raw.get("completion_condition", ""),
            provenance=provenance,
            created_at=raw.get("created_at") or _utcnow(),
            updated_at=raw.get("updated_at") or _utcnow(),
            superseded_by=raw.get("superseded_by"),
            revoked_reason=raw.get("revoked_reason", ""),
            completed_at=raw.get("completed_at"),
        )

    def is_active(self, now_iso: str | None = None) -> bool:
        if self.status != WarrantStatus.ACTIVE:
            return False
        if not self.issuer.strip() or not self.policy_basis.strip():
            return False
        # Finite authority is the default. An exceptional indefinite warrant must
        # be explicit in scope and can be further restricted by policy upstream.
        indefinite = self.scope.get("indefinite_authority_explicit") is True
        if not self.valid_to and not indefinite:
            return False
        try:
            now = _parse_boundary(now_iso, required=True) if now_iso else datetime.now(timezone.utc)
            start = _parse_boundary(self.valid_from, required=True)
            end = _parse_boundary(self.valid_to) if self.valid_to else None
        except ValueError:
            return False
        if start and now < start:
            return False
        if end:
            if end <= start:
                return False
            if now >= end:
                return False
        return True

    def permits(
        self,
        action_type: str,
        domain: str,
        subject: str,
        now_iso: str | None = None,
        *,
        target: str | None = None,
        action_scope: list[str] | tuple[str, ...] | None = None,
        actions_used: int | None = None,
    ) -> bool:
        if not self.is_active(now_iso):
            return False
        if self.domain != domain and self.domain != "general":
            return False
        if self.action_class != action_type and self.action_class != "*":
            return False
        if self.subject and self.subject != subject and self.subject != "*":
            return False

        allowed_subjects = tuple(self.scope.get("subjects") or ())
        if allowed_subjects and subject not in allowed_subjects and "*" not in allowed_subjects:
            return False

        allowed_targets = tuple(self.scope.get("targets") or ())
        effective_target = target if target is not None else self.target
        if allowed_targets and effective_target not in allowed_targets and "*" not in allowed_targets:
            return False
        if self.target and target is not None and self.target not in ("*", target):
            return False

        required_scope = set(action_scope or ())
        allowed_scope = set(self.scope.get("allowed_scope") or ())
        if required_scope and allowed_scope and not required_scope.issubset(allowed_scope):
            return False
        if required_scope and not allowed_scope:
            return False

        max_actions = self.scope.get("max_actions")
        if max_actions is not None:
            try:
                max_actions = int(max_actions)
            except (TypeError, ValueError):
                return False
            if max_actions < 1 or actions_used is None or actions_used >= max_actions:
                return False

        return True

    def expire(self) -> None:
        if self.status == WarrantStatus.ACTIVE:
            self.status = WarrantStatus.EXPIRED
            self.updated_at = _utcnow()

    def revoke(self, reason: str = "") -> None:
        self.status = WarrantStatus.REVOKED
        self.revoked_reason = reason
        self.updated_at = _utcnow()

    def complete(self) -> None:
        self.status = WarrantStatus.COMPLETED
        self.completed_at = _utcnow()
        self.updated_at = _utcnow()

    def require_review(self, reason: str = "") -> None:
        self.status = WarrantStatus.REVIEW_REQUIRED
        self.updated_at = _utcnow()
        if reason:
            self.provenance["review_reason"] = reason

    def supersede(self, by_warrant_id: str) -> None:
        self.status = WarrantStatus.SUPERSEDED
        self.superseded_by = by_warrant_id
        self.updated_at = _utcnow()
