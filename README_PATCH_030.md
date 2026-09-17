# Patch 030 — iCloud Uncertain-Send Reconciliation

An SMTP timeout or connection failure after dispatch may mean the message was sent. StillPoint must never infer "no effect" and blindly retry.

Patch 030 adds a read-only iCloud Sent-mail probe using the deterministic StillPoint RFC822 Message-ID. It discovers the server's `\\Sent` mailbox, searches for the exact Message-ID, and confirms effect only when exactly one match reproduces the authorized From, To, and Subject headers.

Zero matches, multiple matches, missing headers, or mismatched headers remain ambiguous. Reconciliation never restores or reuses the spent warrant.

A provider-neutral `reconcile_mail_send` helper now works with both Gmail and iCloud adapters that expose `probe_existing`.
