-- 009_lifecycle_release_reentry.sql
-- Completion/release/re-entry invariants and atomic authorization state.
-- Forward-only. Migrations 001-008 remain historical.

ALTER TABLE action_requests ADD COLUMN release_id TEXT;
ALTER TABLE action_requests ADD COLUMN reevaluation_trigger_id TEXT;
ALTER TABLE action_requests ADD COLUMN reentry_parent_action_id TEXT;

CREATE INDEX IF NOT EXISTS ix_action_requests_release
ON action_requests(release_id);

CREATE INDEX IF NOT EXISTS ix_action_requests_reevaluation
ON action_requests(reevaluation_trigger_id, reentry_parent_action_id);

-- A request may wait for approval without a warrant, but anything represented
-- as ready or beyond must have explicit authority bound.
CREATE TRIGGER IF NOT EXISTS trg_action_status_requires_warrant
BEFORE UPDATE OF status ON action_requests
WHEN NEW.status IN (
    'ready_for_action','dispatching','completed','failed','uncertain',
    'reconciled_effect','reconciled_no_effect'
)
BEGIN
    SELECT CASE
      WHEN NEW.warrant_id IS NULL OR trim(NEW.warrant_id) = ''
      THEN RAISE(ABORT, 'action state requires explicit warrant binding')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_action_ready_requires_approval
BEFORE UPDATE OF status ON action_requests
WHEN NEW.status = 'ready_for_action' AND NEW.approval_required = 1
BEGIN
    SELECT CASE
      WHEN NEW.approval_id IS NULL OR trim(NEW.approval_id) = ''
      THEN RAISE(ABORT, 'ready action requires bound approval')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_action_release_immutable
BEFORE UPDATE OF release_id ON action_requests
WHEN OLD.release_id IS NOT NULL AND NEW.release_id IS NOT OLD.release_id
BEGIN
    SELECT RAISE(ABORT, 'action release binding is immutable');
END;

CREATE TRIGGER IF NOT EXISTS trg_temporal_release_exact_prior_warrant
BEFORE INSERT ON temporal_releases
BEGIN
    SELECT CASE
      WHEN NEW.prior_warrant_id IS NULL OR trim(NEW.prior_warrant_id) = ''
      THEN RAISE(ABORT, 'release requires prior warrant')
    END;
    SELECT CASE
      WHEN NOT EXISTS (
        SELECT 1 FROM temporal_warrants w
        WHERE w.warrant_id = NEW.prior_warrant_id
          AND w.subject = NEW.subject
          AND w.status = 'completed'
      )
      THEN RAISE(ABORT, 'release must bind exact completed warrant and subject')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_reevaluation_requires_new_evidence
BEFORE INSERT ON temporal_reevaluation_triggers
BEGIN
    SELECT CASE
      WHEN NEW.prior_warrant_id IS NULL OR trim(NEW.prior_warrant_id) = ''
      THEN RAISE(ABORT, 'reevaluation requires prior warrant')
    END;
    SELECT CASE
      WHEN NEW.new_evidence_ids_json IS NULL
        OR NEW.new_evidence_ids_json = '[]'
      THEN RAISE(ABORT, 'reevaluation requires new evidence')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_reentry_never_reuses_old_warrant
BEFORE UPDATE OF warrant_id,reentry_parent_action_id ON action_requests
WHEN NEW.reentry_parent_action_id IS NOT NULL
BEGIN
    SELECT CASE
      WHEN EXISTS (
        SELECT 1
        FROM action_requests prior
        WHERE prior.id = NEW.reentry_parent_action_id
          AND prior.warrant_id = NEW.warrant_id
      )
      THEN RAISE(ABORT, 're-entry cannot reuse prior warrant')
    END;
END;
