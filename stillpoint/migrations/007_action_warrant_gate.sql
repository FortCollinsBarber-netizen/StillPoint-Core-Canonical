-- 007_action_warrant_gate.sql
-- Bind consequential ActionRequests to explicit temporal Warrants.
-- Forward-only. Does not rewrite migrations 001-006.

ALTER TABLE action_requests ADD COLUMN warrant_id TEXT;
ALTER TABLE action_requests ADD COLUMN warrant_bound_at TEXT;

CREATE INDEX IF NOT EXISTS ix_action_requests_warrant
ON action_requests(warrant_id, status);

CREATE TABLE IF NOT EXISTS action_warrant_consumptions (
    action_id TEXT PRIMARY KEY,
    warrant_id TEXT NOT NULL,
    consumed_at TEXT NOT NULL,
    authority_revision TEXT NOT NULL,
    approval_id TEXT,
    artifact_hashes_json TEXT NOT NULL,
    disposition TEXT NOT NULL DEFAULT 'reserved',
    FOREIGN KEY(action_id) REFERENCES action_requests(id),
    FOREIGN KEY(warrant_id) REFERENCES temporal_warrants(warrant_id)
);

CREATE INDEX IF NOT EXISTS ix_action_warrant_consumptions_warrant
ON action_warrant_consumptions(warrant_id, consumed_at);

CREATE TRIGGER IF NOT EXISTS trg_action_request_warrant_binding_immutable
BEFORE UPDATE OF warrant_id ON action_requests
WHEN OLD.warrant_id IS NOT NULL AND NEW.warrant_id IS NOT OLD.warrant_id
BEGIN
    SELECT RAISE(ABORT, 'action warrant binding is immutable');
END;

CREATE TRIGGER IF NOT EXISTS trg_action_consumption_exact_binding
BEFORE INSERT ON action_warrant_consumptions
BEGIN
    SELECT CASE
      WHEN NOT EXISTS (
        SELECT 1 FROM action_requests ar
        WHERE ar.id = NEW.action_id
          AND ar.warrant_id = NEW.warrant_id
          AND ar.authority_revision = NEW.authority_revision
      )
      THEN RAISE(ABORT, 'warrant consumption does not match action binding')
    END;
END;
