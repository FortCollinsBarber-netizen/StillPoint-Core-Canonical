-- 016_signal_gmail_inbox.sql
-- Durable read-only Gmail inbox cursor for Signal.
-- Inbox observation creates evidence/work only; it grants no reply authority.

CREATE TABLE IF NOT EXISTS signal_gmail_mailboxes (
    account TEXT PRIMARY KEY,
    history_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    bootstrap_completed_at TEXT,
    last_polled_at TEXT,
    last_success_at TEXT,
    last_error TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS signal_gmail_poll_receipts (
    receipt_id TEXT PRIMARY KEY,
    account TEXT NOT NULL,
    mode TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    start_history_id TEXT,
    end_history_id TEXT,
    messages_seen INTEGER NOT NULL,
    tasks_created INTEGER NOT NULL,
    status TEXT NOT NULL,
    error TEXT,
    FOREIGN KEY(account) REFERENCES signal_gmail_mailboxes(account)
);
CREATE INDEX IF NOT EXISTS ix_signal_gmail_poll_receipts_account
ON signal_gmail_poll_receipts(account,finished_at,receipt_id);

CREATE TRIGGER IF NOT EXISTS trg_signal_gmail_mailbox_validate_insert
BEFORE INSERT ON signal_gmail_mailboxes BEGIN
  SELECT CASE WHEN trim(NEW.account)='' THEN RAISE(ABORT,'gmail account required') END;
  SELECT CASE WHEN NEW.status NOT IN ('active','paused','resync_required') THEN RAISE(ABORT,'invalid gmail mailbox status') END;
END;
CREATE TRIGGER IF NOT EXISTS trg_signal_gmail_mailbox_validate_update
BEFORE UPDATE ON signal_gmail_mailboxes BEGIN
  SELECT CASE WHEN NEW.status NOT IN ('active','paused','resync_required') THEN RAISE(ABORT,'invalid gmail mailbox status') END;
END;
CREATE TRIGGER IF NOT EXISTS trg_signal_gmail_receipt_validate_insert
BEFORE INSERT ON signal_gmail_poll_receipts BEGIN
  SELECT CASE WHEN NEW.mode NOT IN ('bootstrap','history','resync') THEN RAISE(ABORT,'invalid gmail poll mode') END;
  SELECT CASE WHEN NEW.status NOT IN ('succeeded','failed','history_expired') THEN RAISE(ABORT,'invalid gmail poll status') END;
  SELECT CASE WHEN NEW.messages_seen<0 OR NEW.tasks_created<0 THEN RAISE(ABORT,'invalid gmail poll counts') END;
END;
CREATE TRIGGER IF NOT EXISTS trg_signal_gmail_receipts_no_update BEFORE UPDATE ON signal_gmail_poll_receipts BEGIN SELECT RAISE(ABORT,'gmail poll receipts are append-only'); END;
CREATE TRIGGER IF NOT EXISTS trg_signal_gmail_receipts_no_delete BEFORE DELETE ON signal_gmail_poll_receipts BEGIN SELECT RAISE(ABORT,'gmail poll receipts are append-only'); END;
