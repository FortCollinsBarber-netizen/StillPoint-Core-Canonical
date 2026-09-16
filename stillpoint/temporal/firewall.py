"""Claim-to-warrant, prediction, and domain-containment firewalls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .claims import Claim, ClaimStatus, ClaimDomain
from .warrants import Warrant


class TemporalAuthorityError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"[{code}] {message}")


@dataclass
class ClaimToWarrantFirewall:
    def assert_claim_is_not_warrant(self, claim: Claim) -> None:
        if hasattr(claim, "action_class") or hasattr(claim, "issuer"):
            raise TemporalAuthorityError(
                "CLAIM_AS_WARRANT",
                "Claim objects must not carry action authorization fields",
            )

    def require_warrant_for_action(
        self,
        *,
        action_type: str,
        domain: str,
        subject: str,
        warrants: list[Warrant],
        now_iso: str | None = None,
        target: str | None = None,
        action_scope: list[str] | tuple[str, ...] | None = None,
        usage_by_warrant: dict[str, int] | None = None,
    ) -> Warrant:
        usage_by_warrant = usage_by_warrant or {}
        for warrant in warrants:
            if warrant.permits(
                action_type,
                domain,
                subject,
                now_iso=now_iso,
                target=target,
                action_scope=action_scope,
                actions_used=usage_by_warrant.get(warrant.warrant_id),
            ):
                return warrant
        raise TemporalAuthorityError(
            "NO_ACTIVE_WARRANT",
            f"No active warrant authorizes action_type={action_type!r} "
            f"domain={domain!r} subject={subject!r}",
        )

    def claim_cannot_create_action_authority(self, claim: Claim) -> None:
        if claim.status not in tuple(ClaimStatus):
            raise TemporalAuthorityError(
                "UNKNOWN_CLAIM_STATUS", f"Unrecognized claim status {claim.status}"
            )
        raise TemporalAuthorityError(
            "CLAIM_NOT_AUTHORITY",
            f"Claim {claim.claim_id} is information only; explicit warrant required.",
        )


@dataclass
class PredictionFirewall:
    def assert_prediction_is_evidence_not_authority(
        self,
        *,
        prediction: Any,
        confidence: float | None,
        action_type: str | None = None,
    ) -> None:
        raise TemporalAuthorityError(
            "PREDICTION_NOT_AUTHORITY",
            f"Prediction (confidence={confidence}) is evidence only. "
            f"It cannot authorize action_type={action_type!r}.",
        )

    def prediction_may_become_evidence(
        self, prediction: Any, confidence: float | None = None
    ) -> dict[str, Any]:
        return {
            "kind": "prediction",
            "content": prediction,
            "confidence": confidence,
            "is_authority": False,
        }


@dataclass
class DomainContainment:
    SENSITIVE = {
        ClaimDomain.MEDICAL.value,
        ClaimDomain.CRIMINAL.value,
        ClaimDomain.FINANCIAL.value,
        ClaimDomain.RELIGIOUS.value,
        ClaimDomain.IDENTITY.value,
        ClaimDomain.RISK.value,
    }

    def assert_domain_compatible(
        self,
        claim_domain: str | ClaimDomain,
        warrant_domain: str,
        action_domain: str,
        *,
        explicit_cross_domain_claim_domains: set[str] | None = None,
    ) -> None:
        claim_domain_value = (
            claim_domain.value if isinstance(claim_domain, ClaimDomain) else claim_domain
        )
        if claim_domain_value == action_domain or claim_domain_value == "general":
            return

        explicitly_allowed = explicit_cross_domain_claim_domains or set()
        if claim_domain_value in self.SENSITIVE:
            if (
                claim_domain_value in explicitly_allowed
                and warrant_domain in (action_domain, "general")
            ):
                return
            raise TemporalAuthorityError(
                "CROSS_DOMAIN_PROMOTION",
                f"Sensitive claim domain {claim_domain_value!r} cannot migrate into "
                f"{action_domain!r} without explicit cross-domain warrant scope.",
            )

        if warrant_domain not in (action_domain, "general"):
            raise TemporalAuthorityError(
                "DOMAIN_MISMATCH",
                f"Warrant domain {warrant_domain!r} does not cover {action_domain!r}.",
            )

    def scope_action_leq_warrant(
        self,
        action_type: str,
        action_domain: str,
        action_subject: str,
        warrant: Warrant,
        *,
        action_target: str | None = None,
        action_scope: list[str] | tuple[str, ...] | None = None,
        actions_used: int | None = None,
    ) -> bool:
        return warrant.permits(
            action_type,
            action_domain,
            action_subject,
            target=action_target,
            action_scope=action_scope,
            actions_used=actions_used,
        )
