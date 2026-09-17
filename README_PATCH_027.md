# Patch 027 — Provider-Neutral Mail Contract + First-Class iCloud Transport

StillPoint Signal is no longer conceptually Gmail-first.

This patch introduces a provider-neutral mailbox identity and normalized inbound-message contract, plus bounded iCloud Mail transports using Apple's documented IMAP/SMTP endpoints.

## Boundaries

- mailbox identity is `provider + exact account + jurisdiction`;
- transport never creates authority;
- iCloud inbox access is read-only and UID-cursor based;
- iCloud SMTP sends only one already-authorized plain-text artifact to one exact recipient;
- no CC/BCC/attachments are added by the transport;
- the transport requires a bound warrant and preserves the existing no-blind-retry rule;
- SMTP acceptance is recorded as provider acceptance, not delivery/read proof;
- credentials are injected at runtime only and are never persisted by these classes;
- an Apple app-specific password is required for this direct IMAP/SMTP implementation.

Patch 028 will lift Signal service/governance from Gmail-specific identity to the provider-neutral mailbox identity and support multiple independent mailbox jurisdictions under one Signal office.
