# Patch 020 — Signal Operational Status / CEO Surface

Patch 020 adds a read-only operational status inspector for the first Signal employee. Monitoring is deliberately non-authorizing: it reads durable state and never creates tasks, evaluations, warrants, approvals, dispatches, or worker identities.

The status surface reports Gmail cursor health, most recent poll result, active worker heartbeat, Signal task/decision/action queues, standing-delegation and trigger review windows, finite continuation-facts validity, and uncertain external dispatches that require reconciliation.

The inspector elevates concrete attention states such as `GMAIL_RESYNC_REQUIRED`, `SIGNAL_WORKER_STALE`, `DELEGATION_REVIEW_DUE`, `CONTINUATION_FACTS_EXPIRING`, `HUMAN_REVIEW_QUEUE`, and `UNCERTAIN_EXTERNAL_EFFECT` without treating any of them as authority to act.

Operational command: `python -m stillpoint.signal_status`.
