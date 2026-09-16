-- 008_durable_dispatch_reconciliation.sql
-- Durable external dispatch state machine.
-- Forward-only. Migrations 001-007 remain unchanged.

CREATE TABLE IF NOT EXISTS action_dispatches (
    action_id TEXT PRIMARY KEY,
    warrant_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    adapter TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    authority_revision TEXT NOT NULL,
    approval_id TEXT,
    artifact_hashes_json TEXT NOT NULL,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    result_status TEXT,
    external_id TEXT,
    error TEXT,
    result_evidence_json TEXT NOT NULL DEFAULT '[]',
    reconciled_at TEXT,
    reconciled_by TEXT,
    reconciliation_note TEXT,
    reconciliation_evidence_json TEXT NOT NULL DEFAULT '[]',
    FOREIGN KEY(action_id) REFERENCES action_requests(id),
    FOREIGN KEY(warrant_id) REFERENCES temporal_warrants(warrant_id),
    FOREIGN KEY(task_id) REFERENCES tasks(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_action_dispatch_idempotency
ON action_dispatches(idempotency_key);

CREATE INDEX IF NOT EXISTS ix_action_dispatches_state
ON action_dispatches(state, started_at);

CREATE INDEX IF NOT EXISTS ix_action_dispatches_warrant
ON action_dispatches(warrant_id, state);

CREATE TRIGGER IF NOT EXISTS trg_action_dispatch_state_insert
BEFORE INSERT ON action_dispatches
BEGIN
    SELECT CASE
      WHEN NEW.state != 'dispatching'
      THEN RAISE(ABORT, 'new external dispatch must begin in dispatching state')
    END;
    SELECT CASE
      WHEN trim(COALESCE(NEW.adapter,'')) = ''
        OR NEW.adapter = 'null'
        OR NEW.adapter LIKE 'dry_run%'
      THEN RAISE(ABORT, 'probe adapter cannot create external dispatch record')
    END;
    SELECT CASE
      WHEN NOT EXISTS (
        SELECT 1
        FROM action_requests ar
        WHERE ar.id = NEW.action_id
          AND ar.task_id = NEW.task_id
          AND ar.warrant_id = NEW.warrant_id
          AND ar.idempotency_key = NEW.idempotency_key
          AND ar.authority_revision = NEW.authority_revision
          AND COALESCE(ar.approval_id,'') = COALESCE(NEW.approval_id,'')
      )
      THEN RAISE(ABORT, 'external dispatch does not match action authority binding')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_action_dispatch_state_update
BEFORE UPDATE OF state ON action_dispatches
BEGIN
    SELECT CASE
      WHEN OLD.state = 'dispatching'
        AND NEW.state NOT IN (
          'completed','failed','uncertain',
          'reconciled_effect','reconciled_no_effect'
        )
      THEN RAISE(ABORT, 'invalid dispatch transition from dispatching')
    END;

    SELECT CASE
      WHEN OLD.state = 'uncertain'
        AND NEW.state NOT IN ('reconciled_effect','reconciled_no_effect')
      THEN RAISE(ABORT, 'uncertain dispatch requires reconciliation')
    END;

    SELECT CASE
      WHEN OLD.state IN (
        'completed','failed','reconciled_effect','reconciled_no_effect'
      ) AND NEW.state != OLD.state
      THEN RAISE(ABORT, 'terminal dispatch state is immutable')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_action_dispatch_identity_immutable
BEFORE UPDATE OF action_id,warrant_id,task_id,adapter,idempotency_key,
                 authority_revision,approval_id,artifact_hashes_json
ON action_dispatches
BEGIN
    SELECT RAISE(ABORT, 'dispatch identity and authority binding are immutable');
END;
