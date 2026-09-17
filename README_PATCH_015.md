# Patch 015 — Signal Gmail Inbox Intake

Patch 015 gives Signal a read-only Gmail observation boundary. It uses Gmail history cursors after a bounded Inbox bootstrap, normalizes message metadata and plain-text content into Patch 013 inbound events, and lets event triggers create Signal tasks.

Key invariant: **mail arriving creates evidence/work, never reply authority.** The poller only performs HTTP GET requests. It does not mark read, change labels, draft, send, create ActionRequests, or mint warrants.

History cursor advancement occurs only after every discovered message has been durably ingested/fired. An expired Gmail history cursor enters `resync_required` rather than silently skipping mail. Explicit bounded resync is read-only and remains idempotent through Gmail message-id event deduplication.
