# Patch 012 — Delegated Execution Warrants

Parent candidate: Patch 011 / schema 12.

Schema: **13** via `013_delegated_execution_warrant.sql`.

## Purpose

Patch 012 derives one finite execution warrant from one fresh, current, action-specific standing-delegation evaluation.

Standing delegation still does not equal execution authority.

The chain is now:

`Claim Envelope -> Standing Delegation -> Exact Action Evaluation -> One Execution Warrant -> Existing Dispatch Gate`

## Bounded warrant

A delegated warrant is:

- bound to one exact ActionRequest ID, action type, target, authority revision, scope, and artifact set;
- supported by current Claim Envelopes;
- derived only from the latest current evaluation for that exact action;
- rejected if the evaluation is stale;
- capped by the ActionRequest expiry, standing-delegation review boundary, and a short warrant TTL;
- `max_actions = 1`;
- explicitly marked `authorization_mode = standing_delegation`; and
- prohibited from masquerading as CEO approval.

## Dispatch-time revalidation

`validate_delegated_warrant_current` must be called immediately before the external dispatch boundary. It blocks dispatch if the delegation was revoked/suspended, the review boundary was reached, a newer evaluation superseded the issuing evaluation, a supporting Claim Envelope became former, or the lineage/digest no longer matches.

This patch intentionally does not yet wire that call into `CompanyRuntime.execute_action`; production autonomous external dispatch remains disabled until the runtime integration layer consumes this validator.
