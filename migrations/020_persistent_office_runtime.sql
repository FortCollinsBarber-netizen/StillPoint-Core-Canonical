-- 020_persistent_office_runtime.sql
-- Durable company-office identity, accountable task ownership, and append-only handoff history.
-- Assignment is accountability. Worker lease is temporary execution ownership.
-- Neither grants external-action authority.

CREATE TABLE IF NOT EXISTS office_runtime_state (
    role TEXT PRIMARY KEY,
    desired_state TEXT NOT NULL,
    health_state TEXT NOT NULL,
    current_worker_id TEXT,
    generation INTEGER NOT NULL DEFAULT 0,
    restart_count INTEGER NOT NULL DEFAULT 0,
    last_started_at TEXT,
    last_heartbeat_at TEXT,
    last_completed_at TEXT,
    last_error TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS office_runtime_events (
    event_id TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    worker_id TEXT,
    event_type TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    error TEXT NOT NULL DEFAULT '',
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS ix_office_runtime_events_role ON office_runtime_events(role, occurred_at, event_id);

CREATE TABLE IF NOT EXISTS task_office_assignments (
    task_id TEXT PRIMARY KEY,
    owner_role TEXT NOT NULL,
    assigned_at TEXT NOT NULL,
    assigned_by TEXT NOT NULL,
    reason TEXT NOT NULL,
    handoff_count INTEGER NOT NULL DEFAULT 0,
    state TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES tasks(id)
);
CREATE INDEX IF NOT EXISTS ix_task_office_assignments_owner ON task_office_assignments(owner_role, state, updated_at);

CREATE TABLE IF NOT EXISTS task_office_handoff_events (
    event_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    from_role TEXT,
    to_role TEXT NOT NULL,
    event_type TEXT NOT NULL,
    reason TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(task_id) REFERENCES tasks(id)
);
CREATE INDEX IF NOT EXISTS ix_task_office_handoff_events_task ON task_office_handoff_events(task_id, occurred_at, event_id);

CREATE TRIGGER IF NOT EXISTS trg_office_runtime_state_validate_insert BEFORE INSERT ON office_runtime_state BEGIN
  SELECT CASE WHEN NEW.desired_state NOT IN ('active','paused','stopped') THEN RAISE(ABORT,'invalid office desired state') END;
  SELECT CASE WHEN NEW.health_state NOT IN ('starting','healthy','degraded','stopped') THEN RAISE(ABORT,'invalid office health state') END;
  SELECT CASE WHEN NEW.generation < 0 OR NEW.restart_count < 0 THEN RAISE(ABORT,'invalid office counters') END;
END;
CREATE TRIGGER IF NOT EXISTS trg_office_runtime_state_validate_update BEFORE UPDATE ON office_runtime_state BEGIN
  SELECT CASE WHEN NEW.desired_state NOT IN ('active','paused','stopped') THEN RAISE(ABORT,'invalid office desired state') END;
  SELECT CASE WHEN NEW.health_state NOT IN ('starting','healthy','degraded','stopped') THEN RAISE(ABORT,'invalid office health state') END;
  SELECT CASE WHEN NEW.generation < 0 OR NEW.restart_count < 0 THEN RAISE(ABORT,'invalid office counters') END;
END;
CREATE TRIGGER IF NOT EXISTS trg_office_runtime_events_validate_insert BEFORE INSERT ON office_runtime_events BEGIN
  SELECT CASE WHEN NEW.event_type NOT IN ('started','restarted','healthy','degraded','stopped') THEN RAISE(ABORT,'invalid office runtime event') END;
END;
CREATE TRIGGER IF NOT EXISTS trg_office_runtime_events_no_update BEFORE UPDATE ON office_runtime_events BEGIN SELECT RAISE(ABORT,'office runtime events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS trg_office_runtime_events_no_delete BEFORE DELETE ON office_runtime_events BEGIN SELECT RAISE(ABORT,'office runtime events are append-only'); END;

CREATE TRIGGER IF NOT EXISTS trg_task_office_assignments_validate_insert BEFORE INSERT ON task_office_assignments BEGIN
  SELECT CASE WHEN trim(NEW.owner_role)='' OR trim(NEW.assigned_by)='' OR trim(NEW.reason)='' THEN RAISE(ABORT,'office assignment fields required') END;
  SELECT CASE WHEN NEW.handoff_count < 0 THEN RAISE(ABORT,'invalid handoff count') END;
  SELECT CASE WHEN NEW.state NOT IN ('active','released') THEN RAISE(ABORT,'invalid office assignment state') END;
END;
CREATE TRIGGER IF NOT EXISTS trg_task_office_assignments_validate_update BEFORE UPDATE ON task_office_assignments BEGIN
  SELECT CASE WHEN trim(NEW.owner_role)='' OR trim(NEW.assigned_by)='' OR trim(NEW.reason)='' THEN RAISE(ABORT,'office assignment fields required') END;
  SELECT CASE WHEN NEW.handoff_count < OLD.handoff_count THEN RAISE(ABORT,'handoff count cannot decrease') END;
  SELECT CASE WHEN NEW.state NOT IN ('active','released') THEN RAISE(ABORT,'invalid office assignment state') END;
END;
CREATE TRIGGER IF NOT EXISTS trg_task_office_handoff_events_validate_insert BEFORE INSERT ON task_office_handoff_events BEGIN
  SELECT CASE WHEN NEW.event_type NOT IN ('assigned','handoff','recovered','released') THEN RAISE(ABORT,'invalid office handoff event') END;
  SELECT CASE WHEN trim(NEW.to_role)='' OR trim(NEW.reason)='' THEN RAISE(ABORT,'handoff destination and reason required') END;
END;
CREATE TRIGGER IF NOT EXISTS trg_task_office_handoff_events_no_update BEFORE UPDATE ON task_office_handoff_events BEGIN SELECT RAISE(ABORT,'office handoff events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS trg_task_office_handoff_events_no_delete BEFORE DELETE ON task_office_handoff_events BEGIN SELECT RAISE(ABORT,'office handoff events are append-only'); END;
