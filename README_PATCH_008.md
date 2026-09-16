# Patch 008 — Bounded Gmail Send Boundary

Patch 008 adds the first bounded network adapter for the existing restricted action `send_email`.
It does **not** create a new email authority. Drafting remains non-execution; sending remains a consequential action that requires CEO approval and a finite warrant.

The governing sequence is:

`compose != authorize send != execute send != prove provider acceptance`

## Authorized shape

Patch 008 accepts one plain-text message only. The CEO request must explicitly bind the sending account, recipient, and subject **before approval**, for example:

```text
Send an email from operator@example.com to recipient@example.com subject: Project update
```

The existing ActionRequest already preserves that exact clause as its target/scope and binds the generated artifact version/hash before approval. The Gmail adapter refuses any request that does not contain exactly one sender address, one recipient address, one subject, and exactly one authorized artifact.

No CC, BCC, attachments, replies, forwarding, multi-recipient send, Gmail delete/update operation, draft creation, or public-publishing capability is added.

## Execution gate

The network adapter is disabled by default. Real execution additionally requires:

```bash
export STILLPOINT_GMAIL_ACCOUNT=operator@example.com
export STILLPOINT_ENABLE_GMAIL_SEND=1
export STILLPOINT_GMAIL_ACCESS_TOKEN='short-lived-oauth-token'
```

`STILLPOINT_GMAIL_ACCOUNT` must equal the sender that was already present in the approved ActionRequest. The Gmail API call uses that exact account as `userId`, so changing the configured account after approval cannot redirect an already-authorized send.

For send + reconciliation with one token, use a Gmail OAuth token whose scope permits both `messages.send` and read-only reconciliation operations; `gmail.modify` is one supported Gmail scope for all three methods used by this adapter. Provider credential capacity does not become StillPoint action permission.

## Network ambiguity

The adapter performs no automatic retry. The runtime records the durable dispatch boundary and consumes the one-use warrant before the Gmail call. A timeout, unreadable post-effect response, or other exception therefore becomes `uncertain` under the existing dispatch state machine.

For an uncertain Gmail send:

```bash
python -m stillpoint.cli reconcile-gmail-send ACTION_ID
```

The reconciliation probe is read-only. It searches Sent mail for the deterministic RFC 822 Message-ID belonging to the action, then verifies the Message-ID, From, To, and Subject headers. Zero matches is intentionally left **ambiguous** rather than treated as proof of no effect, so indexing delay cannot silently authorize a retry. A confirmed effect closes the dispatch through the existing reconciliation path; the consumed warrant is never restored.

## Evidence semantics

A successful Gmail `messages.send` response produces StillPoint `delivery_receipt` evidence because that is the existing `send_email` completion criterion. The receipt itself explicitly records that this proves **Gmail provider acceptance**, not recipient reading or final downstream delivery.

Patch 008 also closes the Patch 007 dangling-symlink gap by rejecting symlink path objects even when their targets do not exist.
