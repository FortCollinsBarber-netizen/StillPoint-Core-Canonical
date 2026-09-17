# Patch 021 — Signal Email Safety Firewall

Patch 021 hardens the first autonomous Signal vertical before governance provisioning.

Gmail intake now retains additional evidence needed for safe interpretation: `Authentication-Results`, `Return-Path`, and bounded attachment metadata. Signal preparation applies deterministic checks before model drafting and again before an outgoing ActionRequest is created.

The deterministic safety gate forces human review for differing Reply-To identity, CC/group mail, attachments, truncated bodies, unverifiable/failed SPF-DKIM-DMARC evidence, high-risk financial/legal/security/medical language, insufficient message content, or a draft that introduces consequential commitments. Email content is explicitly treated as untrusted model input.

Production readiness also refuses a standing delegation unless its executable conditions bind the configured Gmail account, require a prepared non-human-review decision, and restrict autonomy to an explicit finite classification set. Free-form exclusion text is not treated as enforcement.

This patch adds no authority. It narrows which messages can reach standing-delegation consideration.
