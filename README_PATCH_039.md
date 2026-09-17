# Patch 039 — Production Intake Integrity

Patch 039 closes two defects exposed by the first live Apple-first Signal deployment.

- A fresh provider-neutral mailbox now establishes a read-only cursor baseline and creates zero historical work before incremental polling begins.
- A transport without an explicit safe baseline capability fails closed rather than reading from the beginning of mailbox history.
- iCloud intake preserves the complete Authentication-Results, ARC-Authentication-Results, and Received-SPF evidence chain for audit while exposing only Apple receiver authentication services inside the receiver trace boundary to the deterministic sender-verification gate.
- Sender authentication parsing is method-aware: an unambiguous DMARC pass is sufficient; otherwise both SPF and DKIM must pass. Conflicting results fail closed.
- No standing delegation, warrant, action boundary, release condition, or autonomous classification is widened by this patch.

The governing rule remains: evidence may improve reachability; improved evidence does not manufacture authority.
