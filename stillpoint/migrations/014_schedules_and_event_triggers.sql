-- 014_schedules_and_event_triggers.sql
-- Durable internal work generation. Triggers create tasks, never external authority.

CREATE TABLE IF NOT EXISTS trigger_definitions (
    trigger_id TEXT PRIMARY KEY,
    owner_role TEXT NOT NULL,
    trigger_kind TEXT NOT NULL,
    source TEXT,
    event_type TEXT,
    goal_template TEXT NOT NULL,
    project TEXT,
    status TEXT NOT NULL,
    valid_from TEXT NOT NULL,
    review_by TEXT NOT NULL,
    next_run_at TEXT,
    interval_seconds INTEGER,
    max_runs INTEGER,
    run_count INTEGER NOT NULL DEFAULT 0,
    catch_up_policy TEXT NOT NULL DEFAULT 'coalesce',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_trigger_definitions_due
ON trigger_definitions(trigger_kind,status,next_run_at,review_by);
CREATE INDEX IF NOT EXISTS ix_trigger_definitions_event
ON trigger_definitions(trigger_kind,status,source,event_type,review_by);

CREATE TABLE IF NOT EXISTS inbound_events (
    event_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    event_type TEXT NOT NULL,
    dedupe_key TEXT NOT NULL UNIQUE,
    occurred_at TEXT NOT NULL,
    received_at TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS ix_inbound_events_type
ON inbound_events(source,event_type,received_at,event_id);

CREATE TABLE IF NOT EXISTS trigger_firings (
    firing_id TEXT PRIMARY KEY,
    trigger_id TEXT NOT NULL,
    event_id TEXT,
    scheduled_for TEXT,
    task_id TEXT NOT NULL UNIQUE,
    idempotency_key TEXT NOT NULL UNIQUE,
    fired_at TEXT NOT NULL,
    FOREIGN KEY(trigger_id) REFERENCES trigger_definitions(trigger_id),
    FOREIGN KEY(event_id) REFERENCES inbound_events(event_id),
    FOREIGN KEY(task_id) REFERENCES tasks(id)
);

CREATE INDEX IF NOT EXISTS ix_trigger_firings_trigger
ON trigger_firings(trigger_id,fired_at,firing_id);

CREATE TRIGGER IF NOT EXISTS trg_trigger_definitions_validate_insert
BEFORE INSERT ON trigger_definitions
BEGIN
    SELECT CASE WHEN NEW.trigger_kind NOT IN ('event','schedule') THEN RAISE(ABORT,'invalid trigger kind') END;
    SELECT CASE WHEN NEW.status NOT IN ('active','paused','stopped','review_required') THEN RAISE(ABORT,'invalid trigger status') END;
    SELECT CASE WHEN trim(NEW.owner_role)='' OR trim(NEW.goal_template)='' THEN RAISE(ABORT,'trigger owner and goal required') END;
    SELECT CASE WHEN julianday(NEW.valid_from) IS NULL OR julianday(NEW.review_by) IS NULL OR julianday(NEW.review_by)<=julianday(NEW.valid_from) THEN RAISE(ABORT,'invalid trigger validity interval') END;
    SELECT CASE WHEN NEW.catch_up_policy!='coalesce' THEN RAISE(ABORT,'unsupported catch-up policy') END;
    SELECT CASE WHEN NEW.trigger_kind='event' AND (NEW.source IS NULL OR trim(NEW.source)='' OR NEW.event_type IS NULL OR trim(NEW.event_type)='' OR NEW.next_run_at IS NOT NULL OR NEW.interval_seconds IS NOT NULL) THEN RAISE(ABORT,'invalid event trigger fields') END;
    SELECT CASE WHEN NEW.trigger_kind='schedule' AND (NEW.next_run_at IS NULL OR julianday(NEW.next_run_at) IS NULL OR NEW.interval_seconds IS NULL OR NEW.interval_seconds<60 OR NEW.source IS NOT NULL OR NEW.event_type IS NOT NULL) THEN RAISE(ABORT,'invalid schedule trigger fields') END;
    SELECT CASE WHEN NEW.max_runs IS NOT NULL AND NEW.max_runs<1 THEN RAISE(ABORT,'invalid max_runs') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_inbound_events_no_update BEFORE UPDATE ON inbound_events BEGIN SELECT RAISE(ABORT,'inbound events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS trg_inbound_events_no_delete BEFORE DELETE ON inbound_events BEGIN SELECT RAISE(ABORT,'inbound events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS trg_trigger_firings_no_update BEFORE UPDATE ON trigger_firings BEGIN SELECT RAISE(ABORT,'trigger firings are append-only'); END;
CREATE TRIGGER IF NOT EXISTS trg_trigger_firings_no_delete BEFORE DELETE ON trigger_firings BEGIN SELECT RAISE(ABORT,'trigger firings are append-only'); END;
