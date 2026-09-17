# Patch 017 — Signal Standing Authorization + Dispatch Revalidation

Patch 017 connects a prepared Signal `send_email` ActionRequest to the standing-delegation / delegated-warrant layers without defining CEO policy itself.

`SignalStandingAuthorizer` records an action-specific assessment from the durable Signal decision, current Claim Envelopes, caller-supplied continuation facts, and exact action target. Only a current in-scope assessment may ask Patch 012 for a short-lived one-use warrant.

The schema patch closes the final race: when an action enters `dispatching`, SQLite rechecks the exact delegation/evaluation/action binding, current review interval, absence of a newer evaluation, current supporting Claim Envelopes, active warrant interval, and standing-facts digest **inside the same durable state transition used by external dispatch**.

Key invariant: **revocation or loss of standing can defeat a previously issued delegated warrant until the actual dispatch commit begins.**
