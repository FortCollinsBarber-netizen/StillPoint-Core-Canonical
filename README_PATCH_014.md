# Patch 014 — Persistent Worker Service

Patch 014 turns Patch 009's durable lease primitives into a persistent service loop without changing external-action authority.

Key invariant: **a worker service can own and advance internal work; it cannot mint or replace a consequential-action warrant.**

It adds append-only execution events plus durable retry/backoff state, role-scoped task selection, exact lease ownership, a separate-connection heartbeat guard for long blocking model/tool calls, stale-worker detection, bounded optional failed-task retry, and a `serve()` loop.

Blocked tasks are never automatically retried. Failed tasks are not retried unless explicitly configured. The service itself creates no action requests, approvals, standing delegations, or temporal warrants.
