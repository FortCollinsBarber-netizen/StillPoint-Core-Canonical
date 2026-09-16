"""Durable temporal claim model.

A claim is information. It never carries implicit authorization to act.
Claims may be true at T1, superseded or not-current at T2, without rewriting history.
Unknown is not coerced to false (? ≠ 0).

Fail-closed rule: malformed temporal state must never broaden "current" status.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_boundary(value: str | None) -> datetime | None:
    """Parse an ISO-8601 boundary.

    None/empty means the boundary was not supplied. A non-empty malformed value
    raises ValueError so callers cannot silently broaden temporal validity.
    """
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception as exc:
        raise ValueError(f"invalid temporal boundary: {value!r}") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"temporal boundary must be timezone-aware: {value!r}")
    return dt.astimezone(timezone.utc)


class ClaimStatus(str, Enum):
    ACTIVE = "active"
    HISTORICAL = "historical"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"
    WITHDRAWN = "withdrawn"
    REVIEW_REQUIRED = "review_required"


class ClaimDomain(str, Enum):
    GENERAL = "general"
    MEDICAL = "medical"
    EMPLOYMENT = "employment"
    FINANCIAL = "financial"
    CRIMINAL = "criminal"
    RELIGIOUS = "religious"
    IDENTITY = "identity"
    OPERATIONAL = "operational"
    RISK = "risk"
    PREDICTION = "prediction"
    OTHER = "other"


@dataclass(frozen=True)
class EvidenceRef:
    evidence_id: str
    kind: str = "observation"
    note: str = ""
    sha256: str = ""
    observed_at: str = ""


@dataclass
class Claim:
    claim_id: str
    subject: str
    predicate: str
    value: Any
    domain: ClaimDomain
    source: str
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    time_observed: str = ""
    time_asserted: str = ""
    effective_from: str | None = None
    effective_to: str | None = None
    confidence: float | None = None
    status: ClaimStatus = ClaimStatus.ACTIVE
    supersedes: str | None = None
    superseded_by: str | None = None
    review_conditions: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utcnow)
    updated_at: str = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if not self.claim_id:
            self.claim_id = str(uuid4())
        if not self.time_asserted:
            self.time_asserted = self.created_at
        if self.confidence is not None and not (0.0 <= float(self.confidence) <= 1.0):
            raise ValueError("confidence must be None or in [0, 1]")

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["domain"] = self.domain.value if isinstance(self.domain, ClaimDomain) else self.domain
        d["status"] = self.status.value if isinstance(self.status, ClaimStatus) else self.status
        d["evidence_refs"] = [
            asdict(e) if hasattr(e, "__dataclass_fields__") else e for e in self.evidence_refs
        ]
        return d

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Claim":
        refs = [
            EvidenceRef(**r) if isinstance(r, dict) else r
            for r in (raw.get("evidence_refs") or [])
        ]

        raw_domain = raw.get("domain", "other")
        if isinstance(raw_domain, ClaimDomain):
            domain = raw_domain
        elif raw_domain in ClaimDomain._value2member_map_:
            domain = ClaimDomain(raw_domain)
        else:
            domain = ClaimDomain.OTHER

        raw_status = raw.get("status")
        if isinstance(raw_status, ClaimStatus):
            status = raw_status
        elif raw_status in ClaimStatus._value2member_map_:
            status = ClaimStatus(raw_status)
        else:
            # Unknown serialized state is not allowed to become ACTIVE.
            status = ClaimStatus.REVIEW_REQUIRED

        provenance = dict(raw.get("provenance") or {})
        if raw_status not in ClaimStatus._value2member_map_ and not isinstance(raw_status, ClaimStatus):
            provenance["deserialization_warning"] = f"unknown_claim_status:{raw_status!r}"

        return cls(
            claim_id=raw["claim_id"],
            subject=raw["subject"],
            predicate=raw["predicate"],
            value=raw.get("value"),
            domain=domain,
            source=raw.get("source", ""),
            evidence_refs=refs,
            time_observed=raw.get("time_observed", ""),
            time_asserted=raw.get("time_asserted", ""),
            effective_from=raw.get("effective_from"),
            effective_to=raw.get("effective_to"),
            confidence=raw.get("confidence"),
            status=status,
            supersedes=raw.get("supersedes"),
            superseded_by=raw.get("superseded_by"),
            review_conditions=list(raw.get("review_conditions") or []),
            provenance=provenance,
            created_at=raw.get("created_at") or _utcnow(),
            updated_at=raw.get("updated_at") or _utcnow(),
        )

    def is_current(self, now_iso: str | None = None) -> bool:
        if self.status != ClaimStatus.ACTIVE:
            return False
        try:
            now = _parse_boundary(now_iso) if now_iso else datetime.now(timezone.utc)
            start = _parse_boundary(self.effective_from)
            end = _parse_boundary(self.effective_to)
        except ValueError:
            return False

        if start and now < start:
            return False
        if end and now >= end:
            return False
        return True

    def mark_historical(self, reason: str = "") -> None:
        self.status = ClaimStatus.HISTORICAL
        self.updated_at = _utcnow()
        if reason:
            self.provenance["historical_reason"] = reason

    def mark_superseded(self, by_claim_id: str) -> None:
        self.status = ClaimStatus.SUPERSEDED
        self.superseded_by = by_claim_id
        self.updated_at = _utcnow()

    def mark_expired(self) -> None:
        self.status = ClaimStatus.EXPIRED
        self.updated_at = _utcnow()

    def mark_review_required(self, condition: str = "") -> None:
        self.status = ClaimStatus.REVIEW_REQUIRED
        self.updated_at = _utcnow()
        if condition and condition not in self.review_conditions:
            self.review_conditions.append(condition)
