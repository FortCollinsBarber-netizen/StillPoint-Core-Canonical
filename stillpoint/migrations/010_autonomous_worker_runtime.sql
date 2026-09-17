-- 010_autonomous_worker_runtime.sql
-- Durable worker identity and task lease ownership for Autonomous Operations.
-- A lease grants temporary ownership of work. It grants no external-action authority.

CREATE TABLE IF NOT EXISTS worker_instances (
    worker_id TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    started_at TEXT NOT NULL,
    last_heartbeat_at TEXT NOT NULL,
    status TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS ix_worker_instances_status
ON worker_instances(status, last_heartbeat_at);

CREATE TABLE IF NOT EXISTS task_worker_leases (
    task_id TEXT PRIMARY KEY,
    worker_id TEXT NOT NULL,
    lease_token TEXT NOT NULL UNIQUE,
    generation INTEGER NOT NULL,
    acquired_at TEXT NOT NULL,
    heartbeat_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    released_at TEXT,
    state TEXT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES tasks(id),
    FOREIGN KEY(worker_id) REFERENCES worker_instances(worker_id)
);

CREATE INDEX IF NOT EXISTS ix_task_worker_leases_worker
ON task_worker_leases(worker_id, state, expires_at);

CREATE INDEX IF NOT EXISTS ix_task_worker_leases_expiry
ON task_worker_leases(state, expires_at);

CREATE TABLE IF NOT EXISTS task_worker_lease_events (
    event_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    worker_id TEXT NOT NULL,
    lease_token TEXT NOT NULL,
    generation INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    prior_worker_id TEXT,
    prior_lease_token TEXT,
    prior_generation INTEGER,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(task_id) REFERENCES tasks(id)
);

CREATE INDEX IF NOT EXISTS ix_task_worker_lease_events_task
ON task_worker_lease_events(task_id, occurred_at, event_id);

CREATE TRIGGER IF NOT EXISTS trg_worker_instances_validate_insert
BEFORE INSERT ON worker_instances
BEGIN
    SELECT CASE
      WHEN trim(NEW.worker_id) = '' OR trim(NEW.role) = ''
      THEN RAISE(ABORT, 'worker id and role required')
    END;
    SELECT CASE
      WHEN NEW.status NOT IN ('active','stopped')
      THEN RAISE(ABORT, 'invalid worker status')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_worker_instances_validate_update
BEFORE UPDATE ON worker_instances
BEGIN
    SELECT CASE
      WHEN NEW.status NOT IN ('active','stopped')
      THEN RAISE(ABORT, 'invalid worker status')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_task_worker_leases_validate_insert
BEFORE INSERT ON task_worker_leases
BEGIN
    SELECT CASE
      WHEN NEW.generation < 1
      THEN RAISE(ABORT, 'lease generation must be positive')
    END;
    SELECT CASE
      WHEN NEW.state NOT IN ('active','released')
      THEN RAISE(ABORT, 'invalid lease state')
    END;
    SELECT CASE
      WHEN julianday(NEW.acquired_at) IS NULL
        OR julianday(NEW.heartbeat_at) IS NULL
        OR julianday(NEW.expires_at) IS NULL
      THEN RAISE(ABORT, 'invalid lease timestamp')
    END;
    SELECT CASE
      WHEN NEW.state = 'active' AND NEW.released_at IS NOT NULL
      THEN RAISE(ABORT, 'active lease cannot be released')
    END;
    SELECT CASE
      WHEN NEW.state = 'released' AND NEW.released_at IS NULL
      THEN RAISE(ABORT, 'released lease requires released_at')
    END;
    SELECT CASE
      WHEN NEW.state = 'active' AND julianday(NEW.expires_at) <= julianday(NEW.heartbeat_at)
      THEN RAISE(ABORT, 'active lease expiry must follow heartbeat')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_task_worker_leases_validate_update
BEFORE UPDATE ON task_worker_leases
BEGIN
    SELECT CASE
      WHEN NEW.generation < 1
      THEN RAISE(ABORT, 'lease generation must be positive')
    END;
    SELECT CASE
      WHEN NEW.state NOT IN ('active','released')
      THEN RAISE(ABORT, 'invalid lease state')
    END;
    SELECT CASE
      WHEN julianday(NEW.acquired_at) IS NULL
        OR julianday(NEW.heartbeat_at) IS NULL
        OR julianday(NEW.expires_at) IS NULL
      THEN RAISE(ABORT, 'invalid lease timestamp')
    END;
    SELECT CASE
      WHEN NEW.state = 'active' AND NEW.released_at IS NOT NULL
      THEN RAISE(ABORT, 'active lease cannot be released')
    END;
    SELECT CASE
      WHEN NEW.state = 'released' AND NEW.released_at IS NULL
      THEN RAISE(ABORT, 'released lease requires released_at')
    END;
    SELECT CASE
      WHEN NEW.state = 'active' AND julianday(NEW.expires_at) <= julianday(NEW.heartbeat_at)
      THEN RAISE(ABORT, 'active lease expiry must follow heartbeat')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_task_worker_lease_events_validate_insert
BEFORE INSERT ON task_worker_lease_events
BEGIN
    SELECT CASE
      WHEN NEW.generation < 1
      THEN RAISE(ABORT, 'event generation must be positive')
    END;
    SELECT CASE
      WHEN NEW.event_type NOT IN ('acquired','renewed','released','expired_takeover')
      THEN RAISE(ABORT, 'invalid lease event type')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_task_worker_lease_events_no_update
BEFORE UPDATE ON task_worker_lease_events
BEGIN
    SELECT RAISE(ABORT, 'worker lease events are append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_task_worker_lease_events_no_delete
BEFORE DELETE ON task_worker_lease_events
BEGIN
    SELECT RAISE(ABORT, 'worker lease events are append-only');
END;
