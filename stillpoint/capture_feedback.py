"""Untrusted Capture77 feedback -> read-only, non-authoritative Core advisory.

No database writes, dispatch, warrants, approval, action execution or network
operations. A caller must independently supply the expected identity/revision
and evidence fingerprint; model/provider assertions cannot supply authority.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping


class FeedbackIntakeError(ValueError):
    """Reject stale, unbound, forged-looking or malformed feedback input."""


@dataclass(frozen=True)
class FeedbackAdvisory:
    case_id: str
    revision: int
    observation_count: int
    active_count: int
    stale_count: int
    recommended_route: str
    requires_human_attention: bool
    source_qualification: str = "operator_asserted_unverified"
    authority: str = "advisory_only_no_warrants"


def _digest(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def intake_feedback(snapshot: Mapping, *, expected_case_id: str,
                    expected_revision: int, expected_evidence_sha256: str) -> FeedbackAdvisory:
    """Validate an externally supplied projection against *separately witnessed* state.

    This method does not independently authenticate the external producer,
    validate cited publications, or establish a human observer's identity.
    It does not promote a Capture77 suggestion to a StillPoint action.
    """
    if not isinstance(snapshot, Mapping):
        raise FeedbackIntakeError("feedback snapshot must be a mapping")
    if not isinstance(expected_case_id, str) or not expected_case_id:
        raise FeedbackIntakeError("separately bound case ID is required")
    if type(expected_revision) is not int or expected_revision < 0:
        raise FeedbackIntakeError("separately bound case revision is required")
    if not _digest(expected_evidence_sha256):
        raise FeedbackIntakeError("separately bound evidence hash is required")
    if (snapshot.get("case_id") != expected_case_id
            or type(snapshot.get("case_revision")) is not int
            or snapshot["case_revision"] != expected_revision
            or snapshot.get("evidence_sha256") != expected_evidence_sha256):
        raise FeedbackIntakeError("feedback case identity/revision/evidence mismatch")
    if (snapshot.get("authority") != "read_only_no_dispatch_no_approval"
            or snapshot.get("qualification") != "operator_asserted_unverified"):
        raise FeedbackIntakeError("feedback may not assert elevated provenance or authority")
    active = snapshot.get("active_observations")
    if not isinstance(active, list) or len(active) > 256:
        raise FeedbackIntakeError("active observations must be a bounded list")
    observed_ids = set()
    stale_count = 0
    attention = False
    for note in active:
        if not isinstance(note, Mapping):
            raise FeedbackIntakeError("feedback entry must be an object")
        obs_id = note.get("id")
        if type(obs_id) is not int or obs_id <= 0 or obs_id in observed_ids:
            raise FeedbackIntakeError("feedback entries require distinct positive IDs")
        observed_ids.add(obs_id)
        if (note.get("case_id") != expected_case_id
                or note.get("observer_provenance") != "operator_asserted_unverified"
                or note.get("verdict") not in {"supports", "contradicts", "uncertain"}
                or note.get("next_action") not in {"no_change", "reinvestigate", "human_review"}):
            raise FeedbackIntakeError("foreign or malformed feedback entry")
        revision = note.get("witnessed_revision")
        if type(revision) is not int or revision < 0 or not _digest(note.get("evidence_sha256")):
            raise FeedbackIntakeError("malformed observation evidence binding")
        current = (revision == expected_revision
                   and note["evidence_sha256"] == expected_evidence_sha256)
        if not current:
            stale_count += 1
        elif note["verdict"] in {"contradicts", "uncertain"} or note["next_action"] == "human_review":
            attention = True
    if stale_count:
        route = "reobserve_stale_evidence"
    elif attention:
        route = "human_review_recommended"
    elif not active:
        route = "no_observation_yet"
    else:
        route = "routine_read_only"
    # Do not trust projection-calculated counts, flags or routing hints.
    n = snapshot.get("observation_count")
    if (type(n) is not int or n < len(active)
            or snapshot.get("active_observation_count") != len(active)
            or snapshot.get("stale_active_count") != stale_count
            or snapshot.get("human_review_recommended") is not attention
            or snapshot.get("suggested_route") != route):
        raise FeedbackIntakeError("projection counts or recommended route are inconsistent")
    return FeedbackAdvisory(
        case_id=expected_case_id, revision=expected_revision,
        observation_count=n, active_count=len(active), stale_count=stale_count,
        recommended_route=route, requires_human_attention=attention,
    )
