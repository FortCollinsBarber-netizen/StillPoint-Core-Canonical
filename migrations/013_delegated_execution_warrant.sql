-- 013_delegated_execution_warrant.sql
-- Bind a fresh standing-delegation evaluation to one finite, one-use temporal warrant.

ALTER TABLE action_requests ADD COLUMN authorization_mode TEXT NOT NULL DEFAULT 'ceo_approval';
ALTER TABLE action_requests ADD COLUMN standing_delegation_id TEXT;
ALTER TABLE action_requests ADD COLUMN standing_evaluation_id TEXT;

CREATE INDEX IF NOT EXISTS ix_action_requests_standing_authority
ON action_requests(authorization_mode, standing_delegation_id, standing_evaluation_id, status);

CREATE TABLE IF NOT EXISTS delegated_warrant_issuances (
    issuance_id TEXT PRIMARY KEY,
    action_id TEXT NOT NULL UNIQUE,
    warrant_id TEXT NOT NULL UNIQUE,
    delegation_id TEXT NOT NULL,
    evaluation_id TEXT NOT NULL,
    issued_at TEXT NOT NULL,
    request_binding_sha256 TEXT NOT NULL,
    supporting_envelopes_json TEXT NOT NULL DEFAULT '[]',
    claim_ids_json TEXT NOT NULL DEFAULT '[]',
    evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    FOREIGN KEY(action_id) REFERENCES action_requests(id),
    FOREIGN KEY(warrant_id) REFERENCES temporal_warrants(warrant_id),
    FOREIGN KEY(delegation_id) REFERENCES standing_delegations(delegation_id),
    FOREIGN KEY(evaluation_id) REFERENCES standing_delegation_evaluations(evaluation_id)
);

CREATE TRIGGER IF NOT EXISTS trg_action_authorization_mode_validate
BEFORE UPDATE OF authorization_mode,standing_delegation_id,standing_evaluation_id ON action_requests
BEGIN
    SELECT CASE
      WHEN NEW.authorization_mode NOT IN ('ceo_approval','standing_delegation')
      THEN RAISE(ABORT, 'invalid action authorization mode')
    END;
    SELECT CASE
      WHEN NEW.authorization_mode='ceo_approval'
        AND (NEW.standing_delegation_id IS NOT NULL OR NEW.standing_evaluation_id IS NOT NULL)
      THEN RAISE(ABORT, 'CEO approval action cannot carry standing delegation lineage')
    END;
    SELECT CASE
      WHEN NEW.authorization_mode='standing_delegation'
        AND (NEW.standing_delegation_id IS NULL OR trim(NEW.standing_delegation_id)=''
          OR NEW.standing_evaluation_id IS NULL OR trim(NEW.standing_evaluation_id)='')
      THEN RAISE(ABORT, 'standing delegation action requires lineage')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_standing_action_ready_requires_exact_lineage
BEFORE UPDATE OF status,warrant_id,authorization_mode,standing_delegation_id,standing_evaluation_id,
                 approval_required,approval_id ON action_requests
WHEN NEW.status='ready_for_action' AND NEW.authorization_mode='standing_delegation'
BEGIN
    SELECT CASE
      WHEN NEW.approval_required != 0 OR NEW.approval_id IS NOT NULL
      THEN RAISE(ABORT, 'standing delegation action must not impersonate CEO approval')
    END;
    SELECT CASE
      WHEN NEW.warrant_id IS NULL OR trim(NEW.warrant_id)=''
      THEN RAISE(ABORT, 'standing delegation action requires bound execution warrant')
    END;
    SELECT CASE
      WHEN NOT EXISTS (
        SELECT 1 FROM standing_delegations d
        WHERE d.delegation_id=NEW.standing_delegation_id AND d.status='active'
      )
      THEN RAISE(ABORT, 'standing delegation is not active')
    END;
    SELECT CASE
      WHEN NOT EXISTS (
        SELECT 1 FROM standing_delegation_evaluations e
        WHERE e.evaluation_id=NEW.standing_evaluation_id
          AND e.delegation_id=NEW.standing_delegation_id
          AND e.action_id=NEW.id
          AND e.action_type=NEW.action_type
          AND e.action_target=NEW.target
          AND e.result='current'
          AND e.action_in_scope=1
      )
      THEN RAISE(ABORT, 'standing evaluation does not match exact action')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_action_standing_lineage_immutable
BEFORE UPDATE OF authorization_mode,standing_delegation_id,standing_evaluation_id ON action_requests
WHEN OLD.warrant_id IS NOT NULL AND (
    NEW.authorization_mode IS NOT OLD.authorization_mode
    OR NEW.standing_delegation_id IS NOT OLD.standing_delegation_id
    OR NEW.standing_evaluation_id IS NOT OLD.standing_evaluation_id
)
BEGIN
    SELECT RAISE(ABORT, 'bound action authorization lineage is immutable');
END;

CREATE TRIGGER IF NOT EXISTS trg_delegated_warrant_issuance_validate
BEFORE INSERT ON delegated_warrant_issuances
BEGIN
    SELECT CASE
      WHEN length(trim(NEW.request_binding_sha256)) != 64
      THEN RAISE(ABORT, 'delegated warrant issuance requires request binding digest')
    END;
    SELECT CASE
      WHEN NEW.supporting_envelopes_json IN ('','[]')
      THEN RAISE(ABORT, 'delegated warrant issuance requires supporting envelopes')
    END;
    SELECT CASE
      WHEN NOT EXISTS (
        SELECT 1 FROM action_requests a
        WHERE a.id=NEW.action_id
          AND a.warrant_id=NEW.warrant_id
          AND a.authorization_mode='standing_delegation'
          AND a.standing_delegation_id=NEW.delegation_id
          AND a.standing_evaluation_id=NEW.evaluation_id
      )
      THEN RAISE(ABORT, 'delegated warrant issuance does not match action binding')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_delegated_warrant_issuances_no_update
BEFORE UPDATE ON delegated_warrant_issuances
BEGIN
    SELECT RAISE(ABORT, 'delegated warrant issuance history is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_delegated_warrant_issuances_no_delete
BEFORE DELETE ON delegated_warrant_issuances
BEGIN
    SELECT RAISE(ABORT, 'delegated warrant issuance history is append-only');
END;
