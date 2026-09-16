"""Mandatory temporal authority gate for consequential ActionRequests."""

from __future__ import annotations

from .firewall import ClaimToWarrantFirewall, TemporalAuthorityError
from .warrants import Warrant

ACTION_DOMAINS = {
    "communicate": "communications",
    "send_email": "communications",
    "email": "communications",
    "publish": "publishing",
    "social": "publishing",
    "social_post": "publishing",
    "export_artifact": "operational",
    "spend": "financial",
    "pay": "financial",
    "purchase": "financial",
    "sign": "legal",
    "delete": "operational",
    "other_external": "operational",
}


def action_domain(action_type: str) -> str:
    key = (action_type or "").strip().lower()
    if key not in ACTION_DOMAINS:
        raise TemporalAuthorityError(
            "UNKNOWN_ACTION_DOMAIN",
            f"No temporal authority domain registered for action_type={action_type!r}",
        )
    return ACTION_DOMAINS[key]


def action_subject(task_id: str) -> str:
    if not task_id:
        raise TemporalAuthorityError("MISSING_ACTION_SUBJECT", "task_id is required")
    return f"task:{task_id}"


def build_ceo_warrant(
    *,
    request,
    approval_id: str,
    issuer: str = "CEO:Robert Emmanuel LaDay",
    policy_basis: str | None = None,
) -> Warrant:
    if not approval_id:
        raise TemporalAuthorityError("MISSING_APPROVAL", "approval_id is required")
    if not request.expires_at or not request.issued_at:
        raise TemporalAuthorityError(
            "MISSING_ACTION_TIME",
            "consequential ActionRequest requires issued_at and expires_at",
        )

    domain = action_domain(request.action_type)
    subject = action_subject(request.task_id)
    artifact_binding = [
        {
            "artifact_id": ref.artifact_id,
            "version": ref.version,
            "sha256": ref.sha256,
            "kind": ref.kind,
        }
        for ref in request.artifact_refs
    ]

    return Warrant(
        warrant_id="",
        domain=domain,
        action_class=request.action_type,
        subject=subject,
        target=request.target,
        issuer=issuer,
        policy_basis=policy_basis or f"explicit_ceo_approval:{approval_id}",
        issued_at=request.issued_at,
        valid_from=request.issued_at,
        valid_to=request.expires_at,
        scope={
            "subjects": [subject],
            "targets": [request.target],
            "allowed_scope": list(request.scope),
            "max_actions": 1,
            "authority_revision": request.authority_revision,
            "artifact_binding": artifact_binding,
            "approval_id": approval_id,
        },
        provenance={
            "source": "ceo_approval",
            "approval_id": approval_id,
            "action_id": request.action_id,
            "task_id": request.task_id,
            "authority_revision": request.authority_revision,
        },
    )


def validate_bound_warrant(
    *,
    request,
    warrant: Warrant,
    now_iso: str,
    actions_used: int,
) -> Warrant:
    if request.warrant_id != warrant.warrant_id:
        raise TemporalAuthorityError(
            "WARRANT_BINDING_MISMATCH",
            "ActionRequest is not bound to the supplied warrant",
        )

    if warrant.scope.get("authority_revision") != request.authority_revision:
        raise TemporalAuthorityError(
            "AUTHORITY_REVISION_MISMATCH",
            "Warrant authority revision does not match ActionRequest",
        )

    if request.approval_required and warrant.scope.get("approval_id") != request.approval_id:
        raise TemporalAuthorityError(
            "APPROVAL_WARRANT_MISMATCH",
            "Warrant is not bound to the ActionRequest approval",
        )

    expected_artifacts = warrant.scope.get("artifact_binding") or []
    actual_artifacts = [
        {
            "artifact_id": ref.artifact_id,
            "version": ref.version,
            "sha256": ref.sha256,
            "kind": ref.kind,
        }
        for ref in request.artifact_refs
    ]
    if expected_artifacts != actual_artifacts:
        raise TemporalAuthorityError(
            "WARRANT_ARTIFACT_MISMATCH",
            "Warrant artifact binding does not match ActionRequest",
        )

    gate = ClaimToWarrantFirewall()
    return gate.require_warrant_for_action(
        action_type=request.action_type,
        domain=action_domain(request.action_type),
        subject=action_subject(request.task_id),
        warrants=[warrant],
        now_iso=now_iso,
        target=request.target,
        action_scope=request.scope,
        usage_by_warrant={warrant.warrant_id: actions_used},
    )
