# Patch 009 — Durable Autonomous Worker Foundation

Patch 009 begins the StillPoint Autonomous Operations layer without granting new external authority.

Its governing invariant is:

> A worker lease grants temporary ownership of work, never authority to perform a consequential external action.

The patch adds:

- durable worker-instance identity and heartbeat state;
- atomic task lease acquisition under SQLite `BEGIN IMMEDIATE`;
- finite lease TTLs and exact-token renewal;
- generation numbers so expired or released ownership cannot silently resurrect;
- expired-lease takeover for interruption recovery;
- exact-token release semantics;
- append-only lease-event history for acquisition, renewal, release, and expired takeover;
- explicit rejection of non-claimable task states.

This patch intentionally does **not** add standing delegation, automatic action warrants, schedules, triggers, inbox monitoring, or any new external-action permission. Existing StillPoint action/warrant gates remain authoritative.

## Acceptance invariants

1. Two workers cannot simultaneously own the same unexpired task lease.
2. An expired lease may be taken over with a new token and incremented generation.
3. A stale worker cannot renew, release, or assert ownership after takeover.
4. A released lease may be reacquired only as a new generation.
5. Lease history is append-only.
6. Acquiring a worker lease does not create or modify an action warrant.
7. Terminal/non-runnable tasks cannot be claimed by this layer.

Patch 009 is the mechanical foundation required before StillPoint introduces standing delegation and continuing-evidence conditions for autonomous external work.
