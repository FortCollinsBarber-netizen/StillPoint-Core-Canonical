# Patch 038 — Production Host Closure

Patch 038 closes the boundary between the canonical Apple-first Signal runtime
and a real macOS production host.

It does not commit credentials and does not make release metadata itself a
production activation.

## Earned changes

- first-class provider-neutral `stillpoint-signal-mail` CLI (`check`, `once`, `serve`);
- side-effect-free provider-neutral readiness validation before live assembly;
- exact governance-digest binding for iCloud service startup;
- macOS per-user LaunchAgent deployment assets;
- macOS Keychain secret retrieval for the iCloud app-specific password and xAI API key;
- no root daemon and no `sudo` requirement;
- explicit stop/status tooling;
- SQLite test-fixture cleanup and a release gate that rejects unclosed SQLite warnings.

## Production boundary

The LaunchAgent is the activation boundary. Provisioning claims, envelopes,
standing delegation, trigger, facts, Keychain entries, and readiness checks may
all exist while Signal remains stopped.

The host starts only after:
1. Patch 038 is merged to canonical `main`;
2. GitHub CI passes on the merge commit;
3. exact approved governance digest is provisioned;
4. current facts/delegation/trigger checks pass;
5. Keychain contains required credentials.

The Apple Account primary password and macOS login password are never accepted
by these scripts.
