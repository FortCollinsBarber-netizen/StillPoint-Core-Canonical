# StillPoint Core Patch 003 — Durable Dispatch / Crash-Reconciliation Boundary

Base: Patch 002 commit `87132ba0ec7e72b677ff1b43ad0dcf45edf9db04`.

## Purpose

Patch 002 made a Warrant mandatory. Patch 003 separates three facts that must never
collapse into one another:

- authority existed
- external dispatch was attempted
- completion was proven

A one-use Warrant is **spent when real external dispatch begins**, not when success
is later proven. That closes the retry hole after timeouts, crashes, malformed
adapter results, and "side effect happened but persistence failed" scenarios.

## Non-negotiable

Once a real external dispatch row exists, the same ActionRequest may never be
automatically dispatched again. `reconciled_no_effect` does not restore the old
Warrant. Retry means new present authorization.
