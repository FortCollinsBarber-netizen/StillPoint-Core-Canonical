# Patch 037 — Apple-First Signal Release Identity Closure

Patch 037 updates release metadata to the architecture already earned by the
integrated source tree.

It does not enable production adapters, start Signal, install credentials, or
embed the CEO approval receipt in the public repository.

The closure aligns:
- schema 19 / migrations 001–019;
- Patch 037 release identity;
- disabled production-capable outbox and Gmail adapters;
- non-auto-started Apple/iCloud Signal mailbox service;
- exact iCloud mailbox + personal_business jurisdiction;
- exact governance policy digest and 30-day review policy;
- release metadata audit expectations.

CEO approval evidence remains external release evidence. Describing a policy
in release metadata is not production activation.
