# StillPoint Core 0.2.0rc2

Patch 007 introduces StillPoint's first bounded production-capable adapter: `bounded_outbox`.

This is intentionally a local, reversible execution boundary rather than a network connector. An approved generated artifact may be exported from durable StillPoint state into one explicitly configured outbox root. The adapter is disabled by default and cannot be resolved unless both the enable flag and allowlist root are configured.

The milestone extends the existing constitutional chain rather than bypassing it:

`ActionRequest -> CEO approval -> finite Warrant -> durable dispatch boundary -> bounded_outbox -> export receipt -> evidence-gated completion -> release`

The adapter does not own authorization. It cannot issue warrants, approve its own action, broaden scope, select an arbitrary destination, or restore a consumed warrant.

No email, public publishing, payment, signing, deletion, destructive operation, or network execution is added in this release candidate.
