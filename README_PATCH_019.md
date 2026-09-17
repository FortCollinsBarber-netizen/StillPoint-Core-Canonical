# Patch 019 — Production Signal Service Assembly

Patch 019 turns the Patch 018 composition into a deployable, fail-closed service boundary. It adds no new authority primitive and no schema migration.

The production service requires explicit configuration for the Gmail identity, live provider, Signal standing delegation, Signal Gmail event trigger, and a finite continuation-facts snapshot. It refuses to start if Gmail send is not explicitly enabled, the delegation/trigger is absent or outside review, the database is below schema 18, or the continuation snapshot is stale.

Continuation facts are not immortal environment booleans. The service reloads a JSON snapshot for each authorization consideration. The snapshot must contain `observed_at`, `valid_until`, and `facts`; optional per-envelope facts live under `envelopes`. When `valid_until` is reached, no new autonomous warrant consideration can succeed until the facts are refreshed.

The service exposes three operational commands through `python -m stillpoint.signal_service`:

- `check` — startup/readiness validation with secrets redacted;
- `once` — one Gmail intake + worker drain tick;
- `serve` — persistent employee loop.

Patch 019 intentionally does not create its own delegation or Gmail trigger. Those are governance/configuration objects and must exist before the employee is allowed to run.
