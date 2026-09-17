-- Patch 028: provider-neutral mailbox jurisdictions for Signal.
-- Existing Gmail tables remain for compatibility; new provider-neutral state is additive.

CREATE TABLE IF NOT EXISTS signal_mailboxes (
    mailbox_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL CHECK(provider IN ('gmail','icloud')),
    account TEXT NOT NULL,
    jurisdiction TEXT NOT NULL,
    cursor TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','resync_required','stopped')),
    trigger_id TEXT NOT NULL,
    last_polled_at TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(provider,account,jurisdiction),
    FOREIGN KEY(trigger_id) REFERENCES trigger_definitions(trigger_id)
);

CREATE TABLE IF NOT EXISTS signal_mail_poll_receipts (
    receipt_id TEXT PRIMARY KEY,
    mailbox_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    cursor_before TEXT,
    cursor_after TEXT,
    messages_seen INTEGER NOT NULL DEFAULT 0,
    tasks_created INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    error TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    FOREIGN KEY(mailbox_id) REFERENCES signal_mailboxes(mailbox_id)
);

CREATE INDEX IF NOT EXISTS ix_signal_mail_poll_receipts_mailbox
ON signal_mail_poll_receipts(mailbox_id,finished_at);

ALTER TABLE signal_email_decisions ADD COLUMN mail_provider TEXT NOT NULL DEFAULT 'gmail';
ALTER TABLE signal_email_decisions ADD COLUMN mail_jurisdiction TEXT NOT NULL DEFAULT 'legacy';

CREATE INDEX IF NOT EXISTS ix_signal_email_decisions_mailbox
ON signal_email_decisions(mail_provider,account,mail_jurisdiction,created_at);
