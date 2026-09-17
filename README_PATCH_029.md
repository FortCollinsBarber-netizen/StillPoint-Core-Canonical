# Patch 029 — Apple-First Provider-Neutral Signal Service

This patch turns the Patch 027/028 mail abstractions into an operational service assembly.

One service instance owns exactly one mailbox jurisdiction. The service refuses startup unless the configured standing delegation binds the exact provider, exact mailbox account, exact jurisdiction, prepared reply state, no-human-review state, and a finite classification set.

For iCloud, inbox and send use the bounded Patch 027 IMAP/SMTP transport with an app-specific password injected only at runtime. For Gmail, the existing Gmail poll/send adapters remain available for institutional mail such as CCU.

No mailbox credential is persisted. No mailbox automatically inherits standing from another mailbox. A fleet supervisor may run multiple instances under the Signal office while failures and authority remain isolated.
