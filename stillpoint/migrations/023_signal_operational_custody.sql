-- 023_signal_operational_custody.sql
-- Close the SQLite/filesystem governance materialization gap and make Signal
-- daemon degradation durably observable.

CREATE TABLE IF NOT EXISTS signal_governance_materializations (
    governance_sha256 TEXT NOT NULL,
    facts_path TEXT NOT NULL,
    delegation_id TEXT NOT NULL,
    trigger_id TEXT NOT NULL,
    facts_sha256 TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending','materialized','failed')),
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    materialized_at TEXT,
    PRIMARY KEY(governance_sha256, facts_path)
);

CREATE TABLE IF NOT EXISTS signal_governance_materialization_events (
    event_id TEXT PRIMARY KEY,
    governance_sha256 TEXT NOT NULL,
    facts_path TEXT NOT NULL,
    facts_sha256 TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending','materialized','failed')),
    error TEXT,
    occurred_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_signal_governance_materialization_events_policy
ON signal_governance_materialization_events(governance_sha256, occurred_at);

CREATE TRIGGER IF NOT EXISTS trg_signal_governance_materialization_events_no_update
BEFORE UPDATE ON signal_governance_materialization_events BEGIN
  SELECT RAISE(ABORT,'signal governance materialization events are append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_signal_governance_materialization_events_no_delete
BEFORE DELETE ON signal_governance_materialization_events BEGIN
  SELECT RAISE(ABORT,'signal governance materialization events are append-only');
END;

CREATE TABLE IF NOT EXISTS signal_service_health_events (
    event_id TEXT PRIMARY KEY,
    service TEXT NOT NULL,
    worker_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('healthy','degraded','recovered','stopped')),
    error TEXT,
    detail_json TEXT NOT NULL DEFAULT '{}',
    occurred_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_signal_service_health_events_worker
ON signal_service_health_events(service, worker_id, occurred_at);

CREATE TRIGGER IF NOT EXISTS trg_signal_service_health_events_no_update
BEFORE UPDATE ON signal_service_health_events BEGIN
  SELECT RAISE(ABORT,'signal service health events are append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_signal_service_health_events_no_delete
BEFORE DELETE ON signal_service_health_events BEGIN
  SELECT RAISE(ABORT,'signal service health events are append-only');
END;
