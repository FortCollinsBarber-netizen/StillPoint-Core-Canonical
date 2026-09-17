# Patch 036 — Authority Audit Precision Closure

Patch 036 changes no runtime authority or external-action behavior.

It hardens the repository-wide action-boundary audit so the audit matches the
earned provider-neutral Signal architecture without broad file-level exemptions.

## Changes

- Distinguishes adapter execution from ordinary SQLite `.execute()` calls.
- Treats Signal email preparation as safe only when AST proves:
  - action_type == `send_email`
  - approval_required == True
  - approval_id == None
  - no pre-bound warrant
  - success criteria == `provider_acceptance_receipt`
- Allows durable Signal persistence only in the same exact preparation function.
- Allows direct `action_requests` SQL in delegated warrant issuance only inside
  `DelegatedWarrantIssuer.authorize_waiting_action`.
- Adds adversarial tests proving broader shapes still fail.

No credentials, live authority, or production activation are included.
