-- 015_worker_service_runtime.sql
-- Durable execution attempt/retry state for persistent worker services.
-- Worker service state grants no action authority.

CREATE TABLE IF NOT EXISTS worker_task_retry_state (
    task_id TEXT PRIMARY KEY,
    failure_count INTEGER NOT NULL DEFAULT 0,
    next_eligible_at TEXT,
    last_outcome TEXT,
    exhausted INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS worker_task_execution_events (
    event_id TEXT PRIMARY KEY,
    attempt_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    worker_id TEXT NOT NULL,
    lease_token TEXT NOT NULL,
    generation INTEGER NOT NULL,
    role TEXT NOT NULL,
    event_type TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    retry_after TEXT,
    error TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(task_id) REFERENCES tasks(id)
);

CREATE INDEX IF NOT EXISTS ix_worker_task_execution_task
ON worker_task_execution_events(task_id,occurred_at,event_id);
CREATE INDEX IF NOT EXISTS ix_worker_task_retry_eligible
ON worker_task_retry_state(exhausted,next_eligible_at);

CREATE TRIGGER IF NOT EXISTS trg_worker_task_retry_validate_insert
BEFORE INSERT ON worker_task_retry_state
BEGIN
    SELECT CASE WHEN NEW.failure_count < 0 THEN RAISE(ABORT,'negative worker failure count') END;
    SELECT CASE WHEN NEW.exhausted NOT IN (0,1) THEN RAISE(ABORT,'invalid exhausted flag') END;
    SELECT CASE WHEN NEW.last_outcome IS NOT NULL AND NEW.last_outcome NOT IN ('succeeded','failed','blocked','lease_lost') THEN RAISE(ABORT,'invalid worker outcome') END;
END;
CREATE TRIGGER IF NOT EXISTS trg_worker_task_retry_validate_update
BEFORE UPDATE ON worker_task_retry_state
BEGIN
    SELECT CASE WHEN NEW.failure_count < 0 THEN RAISE(ABORT,'negative worker failure count') END;
    SELECT CASE WHEN NEW.exhausted NOT IN (0,1) THEN RAISE(ABORT,'invalid exhausted flag') END;
    SELECT CASE WHEN NEW.last_outcome IS NOT NULL AND NEW.last_outcome NOT IN ('succeeded','failed','blocked','lease_lost') THEN RAISE(ABORT,'invalid worker outcome') END;
END;
CREATE TRIGGER IF NOT EXISTS trg_worker_task_execution_validate_insert
BEFORE INSERT ON worker_task_execution_events
BEGIN
    SELECT CASE WHEN NEW.generation < 1 THEN RAISE(ABORT,'invalid worker generation') END;
    SELECT CASE WHEN NEW.event_type NOT IN ('started','succeeded','failed','blocked','lease_lost') THEN RAISE(ABORT,'invalid worker execution event') END;
END;
CREATE TRIGGER IF NOT EXISTS trg_worker_task_execution_no_update BEFORE UPDATE ON worker_task_execution_events BEGIN SELECT RAISE(ABORT,'worker execution events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS trg_worker_task_execution_no_delete BEFORE DELETE ON worker_task_execution_events BEGIN SELECT RAISE(ABORT,'worker execution events are append-only'); END;
