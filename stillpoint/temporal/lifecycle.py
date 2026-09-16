"""Temporal lifecycle: completion, release, continuing evidence, and bounded re-entry.

This module formalizes the second outer wall of StillPoint:

    historical success != continuing authority

A consumed/completed warrant may remain true history while having no future
jurisdiction. Release records that authority has ended without deleting history.
New evidence may open a new evaluation cycle, but re-entry requires a new warrant.
"""

from __future__ import annotations

from typing import Iterable

from .evidence import EvidenceEvent
from .reentry import ReleaseRecord, ReevaluationTrigger
from .warrants import Warrant, WarrantStatus
from .firewall import TemporalAuthorityError


def build_action_release(
    *,
    action_id: str,
    warrant: Warrant,
    reason: str,
) -> ReleaseRecord:
    """Create a release receipt for already-consumed authority.

    Patch 003 consumes the one-use warrant when real dispatch begins. Therefore
    lifecycle release records the end of jurisdiction; it does not re-complete or
    resurrect the warrant.
    """
    if not action_id:
        raise ValueError("action_id required")
    if warrant.status != WarrantStatus.COMPLETED:
        raise TemporalAuthorityError(
            "RELEASE_REQUIRES_CONSUMED_WARRANT",
            f"release requires completed/consumed warrant, got {warrant.status.value}",
        )
    return ReleaseRecord(
        release_id="",
        subject=warrant.subject,
        prior_warrant_id=warrant.warrant_id,
        prior_claim_ids=list(warrant.claim_ids),
        released_authority=f"{warrant.domain}:{warrant.action_class}",
        reason=reason,
        provenance={
            "action_id": action_id,
            "warrant_id": warrant.warrant_id,
            "warrant_status_at_release": warrant.status.value,
            "authority_revision": warrant.scope.get("authority_revision", ""),
        },
    )


def build_reevaluation_trigger(
    *,
    prior_disposition: str,
    prior_action_id: str,
    prior_warrant: Warrant,
    evidence: Iterable[EvidenceEvent],
    reason: str,
) -> ReevaluationTrigger:
    evidence = list(evidence)
    if not evidence:
        raise ValueError("new evidence required for reevaluation")
    if any(item.subject != prior_warrant.subject for item in evidence):
        raise TemporalAuthorityError(
            "REEVALUATION_SUBJECT_MISMATCH",
            "new evidence subject must match the prior warrant subject",
        )
    return ReevaluationTrigger(
        trigger_id="",
        prior_disposition=prior_disposition,
        prior_task_id=prior_action_id,
        prior_warrant_id=prior_warrant.warrant_id,
        prior_claim_ids=list(prior_warrant.claim_ids),
        new_evidence_ids=[item.evidence_id for item in evidence],
        reason=reason,
        provenance={
            "prior_action_id": prior_action_id,
            "prior_warrant_status": prior_warrant.status.value,
        },
    )


def assert_bounded_reentry(
    *,
    prior_warrant: Warrant,
    candidate_warrant: Warrant,
    trigger: ReevaluationTrigger,
) -> None:
    """Require re-entry to be a genuinely new authority decision."""
    if not trigger.new_evidence_ids:
        raise TemporalAuthorityError(
            "REENTRY_WITHOUT_NEW_EVIDENCE",
            "re-entry requires new evidence",
        )
    if trigger.prior_warrant_id != prior_warrant.warrant_id:
        raise TemporalAuthorityError(
            "REENTRY_TRIGGER_MISMATCH",
            "trigger does not refer to the prior warrant",
        )
    if candidate_warrant.warrant_id == prior_warrant.warrant_id:
        raise TemporalAuthorityError(
            "OLD_WARRANT_RESURRECTION",
            "re-entry may not reuse or resurrect the prior warrant",
        )
    if candidate_warrant.subject != prior_warrant.subject:
        raise TemporalAuthorityError(
            "REENTRY_SUBJECT_MISMATCH",
            "candidate warrant subject changed across re-entry",
        )
    if candidate_warrant.status != WarrantStatus.ACTIVE:
        raise TemporalAuthorityError(
            "REENTRY_WARRANT_NOT_ACTIVE",
            "candidate re-entry warrant must be a new active warrant",
        )
    if not candidate_warrant.is_active():
        raise TemporalAuthorityError(
            "REENTRY_WARRANT_NOT_CURRENT",
            "candidate re-entry warrant is not currently valid",
        )


def old_authority_never_reactivates(warrant: Warrant) -> None:
    """Explicit assertion helper for tests/audits."""
    if warrant.status == WarrantStatus.ACTIVE:
        raise TemporalAuthorityError(
            "HISTORICAL_AUTHORITY_REACTIVATED",
            "prior consumed authority must not become active again",
        )
