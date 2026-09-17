# Patch 038 Resource Gate Correction

This is a recovery correction to the not-yet-merged Patch 038 working tree.

The first Patch 038 run correctly stopped before production activation, but its
SQLite warning gate was overbroad: it equated ResourceWarnings emitted by
historical test fixtures with production service DB ownership.

The corrected release boundary keeps the full functional suite mandatory and
adds a strict isolated production lifecycle audit. The isolated audit:

- provisions the exact approved Apple-first governance;
- executes provider-neutral readiness;
- assembles the live Signal mailbox service with the mock model provider;
- invokes no inbox poll, SMTP send, or external network action;
- closes the production assembly;
- forces garbage collection with ResourceWarning promoted to an exception;
- fails on any unclosed SQLite connection.

The audit is included as a normal unittest, so GitHub CI executes it on the
repository's Python 3.11 and Python 3.13 matrix.

Historical test-fixture ResourceWarnings remain visible maintenance debt but do
not stand in for production lifecycle evidence.
