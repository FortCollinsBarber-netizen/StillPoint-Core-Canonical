-- 017_signal_email_preparation.sql
-- Durable Signal interpretation / reply-preparation record.
-- A prepared reply remains a proposed action and carries no execution authority.

CREATE TABLE IF NOT EXISTS signal_email_decisions (
    decision_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    account TEXT NOT NULL,
    sender TEXT,
    reply_target TEXT,
    disposition TEXT NOT NULL,
    classification TEXT NOT NULL,
    requires_human INTEGER NOT NULL,
    reason TEXT,
    facts_json TEXT NOT NULL DEFAULT '{}',
    artifact_id TEXT,
    action_id TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(task_id,message_id),
    FOREIGN KEY(task_id) REFERENCES tasks(id),
    FOREIGN KEY(action_id) REFERENCES action_requests(id)
);
CREATE INDEX IF NOT EXISTS ix_signal_email_decisions_message ON signal_email_decisions(account,message_id,created_at);
CREATE TRIGGER IF NOT EXISTS trg_signal_email_decision_validate_insert BEFORE INSERT ON signal_email_decisions BEGIN
  SELECT CASE WHEN NEW.disposition NOT IN ('draft_reply','no_reply','human_review') THEN RAISE(ABORT,'invalid Signal disposition') END;
  SELECT CASE WHEN NEW.requires_human NOT IN (0,1) THEN RAISE(ABORT,'invalid human-review flag') END;
  SELECT CASE WHEN NEW.disposition='draft_reply' AND (NEW.artifact_id IS NULL OR NEW.action_id IS NULL) THEN RAISE(ABORT,'draft reply requires artifact and action') END;
  SELECT CASE WHEN NEW.disposition!='draft_reply' AND NEW.action_id IS NOT NULL THEN RAISE(ABORT,'non-reply decision cannot bind action') END;
END;
CREATE TRIGGER IF NOT EXISTS trg_signal_email_decisions_no_update BEFORE UPDATE ON signal_email_decisions BEGIN SELECT RAISE(ABORT,'Signal email decisions are append-only'); END;
CREATE TRIGGER IF NOT EXISTS trg_signal_email_decisions_no_delete BEFORE DELETE ON signal_email_decisions BEGIN SELECT RAISE(ABORT,'Signal email decisions are append-only'); END;
