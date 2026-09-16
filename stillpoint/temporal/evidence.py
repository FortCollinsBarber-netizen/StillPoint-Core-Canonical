"""Continuing evidence ingress.

Evidence objects are immutable after construction. Persistence hardening in
migration 006 prevents ordinary UPDATE/DELETE of recorded temporal evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4
import hashlib
import json


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_content_sha256(content: Any) -> str:
    payload = json.dumps(
        content,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class EvidenceKind(str, Enum):
    OBSERVATION = "observation"
    DOCUMENT = "document"
    MODEL_OUTPUT = "model_output"
    HUMAN_STATEMENT = "human_statement"
    SYSTEM_EVENT = "system_event"
    PREDICTION = "prediction"
    CORRECTION = "correction"
    OTHER = "other"


@dataclass(frozen=True)
class EvidenceEvent:
    evidence_id: str
    kind: EvidenceKind
    subject: str
    content: Any
    source: str
    observed_at: str = ""
    recorded_at: str = field(default_factory=_utcnow)
    related_claim_ids: list[str] = field(default_factory=list)
    related_warrant_ids: list[str] = field(default_factory=list)
    sha256: str = ""
    confidence: float | None = None
    tags: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.evidence_id:
            object.__setattr__(self, "evidence_id", str(uuid4()))
        if not self.observed_at:
            object.__setattr__(self, "observed_at", self.recorded_at)
        if isinstance(self.kind, str):
            object.__setattr__(
                self,
                "kind",
                EvidenceKind(self.kind) if self.kind in EvidenceKind._value2member_map_ else EvidenceKind.OTHER,
            )
        if self.confidence is not None and not (0.0 <= float(self.confidence) <= 1.0):
            raise ValueError("confidence must be None or in [0, 1]")
        calculated = _canonical_content_sha256(self.content)
        if self.sha256 and self.sha256 != calculated:
            raise ValueError("evidence sha256 does not match canonical content")
        if not self.sha256:
            object.__setattr__(self, "sha256", calculated)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value if isinstance(self.kind, EvidenceKind) else self.kind
        return d

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "EvidenceEvent":
        kind = raw.get("kind", "other")
        if isinstance(kind, str):
            kind = EvidenceKind(kind) if kind in EvidenceKind._value2member_map_ else EvidenceKind.OTHER
        return cls(
            evidence_id=raw["evidence_id"],
            kind=kind,
            subject=raw["subject"],
            content=raw.get("content"),
            source=raw.get("source", ""),
            observed_at=raw.get("observed_at", ""),
            recorded_at=raw.get("recorded_at") or _utcnow(),
            related_claim_ids=list(raw.get("related_claim_ids") or []),
            related_warrant_ids=list(raw.get("related_warrant_ids") or []),
            sha256=raw.get("sha256", ""),
            confidence=raw.get("confidence"),
            tags=list(raw.get("tags") or []),
            provenance=dict(raw.get("provenance") or {}),
        )
