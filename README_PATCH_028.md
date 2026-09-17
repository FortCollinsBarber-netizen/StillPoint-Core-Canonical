# Patch 028 — Multi-Mailbox Signal Jurisdictions

Signal is one office, but each mailbox is an independent jurisdiction.

This patch adds provider-neutral mailbox state, generic intake, provider-aware reply preparation, and provider/account/jurisdiction-bound standing delegation construction.

## Governing rule

Authority for one mailbox cannot be inherited by another mailbox, even when the same human owns both. A proposed email must match all three execution facts:

- `signal_email.provider`
- `signal_email.account`
- `signal_email.jurisdiction`

## Compatibility

Existing Gmail intake remains valid. New iCloud intake from Patch 027 emits the same normalized `message_received` event shape. Existing Signal decisions are migrated as `gmail / legacy`; new decisions persist their provider and jurisdiction explicitly.

No credential material, delegation installation, warrant issuance, or send enablement is performed by this patch.
