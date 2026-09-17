# Patch 032 — Single-Mailbox Apple Governance Closure

Patch 032 records the corrected CEO operating topology for Signal: one autonomous mail account only.

- provider: `icloud`
- account: `fortcollinsbarber@icloud.com`
- jurisdiction: `personal_business`
- autonomous routine classifications: `scheduling`, `acknowledgement`, `routine_information`
- mandatory governance review: 30 days

The CCU Gmail account is deliberately outside this autonomous standing. It remains a school-only exception and receives no Signal delegation from this policy.

Patch 032 adds provider-neutral governance bootstrap/provisioning so the Apple-first mailbox no longer depends on the older Gmail-specific governance installer. Bootstrap creates three deterministic claims/envelopes and **no authority**. Applying the governance spec requires explicit CEO confirmation of the exact SHA-256 and then creates exactly one Signal standing delegation and one iCloud `message_received` trigger.

No Apple Account password or app-specific password is contained in this patch or policy draft.
