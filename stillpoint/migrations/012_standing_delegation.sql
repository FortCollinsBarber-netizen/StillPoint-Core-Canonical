-- 012_standing_delegation.sql
-- Reusable bounded delegation standing. This layer does not mint execution warrants.

CREATE TABLE IF NOT EXISTS standing_delegations (
    delegation_id TEXT PRIMARY KEY,
    delegate_role TEXT NOT NULL,
    issuer TEXT NOT NULL,
    policy_basis TEXT NOT NULL,
    purpose TEXT NOT NULL,
    claim_envelope_ids_json TEXT NOT NULL DEFAULT '[]',
    allowed_action_types_json TEXT NOT NULL DEFAULT '[]',
    continuation_conditions_json TEXT NOT NULL DEFAULT '[]',
    execution_conditions_json TEXT NOT NULL DEFAULT '[]',
    exclusions_json TEXT NOT NULL DEFAULT '[]',
    release_conditions_json TEXT NOT NULL DEFAULT '[]',
    valid_from TEXT NOT NULL,
    review_by TEXT NOT NULL,
    status TEXT NOT NULL,
    supersedes_delegation_id TEXT,
    superseded_by_delegation_id TEXT,
    revoked_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(supersedes_delegation_id) REFERENCES standing_delegations(delegation_id),
    FOREIGN KEY(superseded_by_delegation_id) REFERENCES standing_delegations(delegation_id)
);

CREATE INDEX IF NOT EXISTS ix_standing_delegations_role_status
ON standing_delegations(delegate_role, status, review_by);

CREATE TABLE IF NOT EXISTS standing_delegation_evaluations (
    evaluation_id TEXT PRIMARY KEY,
    delegation_id TEXT NOT NULL,
    evaluated_at TEXT NOT NULL,
    action_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    action_target TEXT NOT NULL,
    facts_sha256 TEXT NOT NULL,
    result TEXT NOT NULL,
    action_in_scope INTEGER NOT NULL,
    failed_conditions_json TEXT NOT NULL DEFAULT '[]',
    supporting_envelopes_json TEXT NOT NULL DEFAULT '[]',
    note TEXT NOT NULL DEFAULT '',
    FOREIGN KEY(delegation_id) REFERENCES standing_delegations(delegation_id),
    FOREIGN KEY(action_id) REFERENCES action_requests(id)
);

CREATE INDEX IF NOT EXISTS ix_standing_delegation_evaluations_delegation
ON standing_delegation_evaluations(delegation_id, evaluated_at, evaluation_id);

CREATE TRIGGER IF NOT EXISTS trg_standing_delegations_validate_insert
BEFORE INSERT ON standing_delegations
BEGIN
    SELECT CASE
      WHEN NEW.status NOT IN ('active','suspended','revoked','expired','superseded','review_required')
      THEN RAISE(ABORT, 'invalid standing delegation status')
    END;
    SELECT CASE
      WHEN trim(NEW.delegate_role)='' OR trim(NEW.issuer)='' OR trim(NEW.policy_basis)='' OR trim(NEW.purpose)=''
      THEN RAISE(ABORT, 'standing delegation identity and policy basis required')
    END;
    SELECT CASE
      WHEN NEW.claim_envelope_ids_json IN ('','[]')
        OR NEW.allowed_action_types_json IN ('','[]')
        OR NEW.continuation_conditions_json IN ('','[]')
        OR NEW.execution_conditions_json IN ('','[]')
        OR NEW.release_conditions_json IN ('','[]')
      THEN RAISE(ABORT, 'standing delegation requires bounded scope and continuation conditions')
    END;
    SELECT CASE
      WHEN julianday(NEW.valid_from) IS NULL OR julianday(NEW.review_by) IS NULL
      THEN RAISE(ABORT, 'invalid standing delegation time boundary')
    END;
    SELECT CASE
      WHEN julianday(NEW.review_by) <= julianday(NEW.valid_from)
      THEN RAISE(ABORT, 'standing delegation review_by must follow valid_from')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_standing_delegations_validate_update
BEFORE UPDATE ON standing_delegations
BEGIN
    SELECT CASE
      WHEN NEW.status NOT IN ('active','suspended','revoked','expired','superseded','review_required')
      THEN RAISE(ABORT, 'invalid standing delegation status')
    END;
    SELECT CASE
      WHEN NEW.delegation_id IS NOT OLD.delegation_id
        OR NEW.delegate_role IS NOT OLD.delegate_role
        OR NEW.issuer IS NOT OLD.issuer
        OR NEW.policy_basis IS NOT OLD.policy_basis
        OR NEW.purpose IS NOT OLD.purpose
        OR NEW.claim_envelope_ids_json IS NOT OLD.claim_envelope_ids_json
        OR NEW.allowed_action_types_json IS NOT OLD.allowed_action_types_json
        OR NEW.continuation_conditions_json IS NOT OLD.continuation_conditions_json
        OR NEW.execution_conditions_json IS NOT OLD.execution_conditions_json
        OR NEW.exclusions_json IS NOT OLD.exclusions_json
        OR NEW.release_conditions_json IS NOT OLD.release_conditions_json
        OR NEW.valid_from IS NOT OLD.valid_from
        OR NEW.review_by IS NOT OLD.review_by
        OR NEW.supersedes_delegation_id IS NOT OLD.supersedes_delegation_id
        OR NEW.created_at IS NOT OLD.created_at
      THEN RAISE(ABORT, 'standing delegation contract fields are immutable; supersede instead')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_standing_delegation_evaluations_validate_insert
BEFORE INSERT ON standing_delegation_evaluations
BEGIN
    SELECT CASE
      WHEN NEW.result NOT IN ('current','former','review_required')
      THEN RAISE(ABORT, 'invalid standing delegation evaluation result')
    END;
    SELECT CASE
      WHEN NEW.action_in_scope NOT IN (0,1)
      THEN RAISE(ABORT, 'invalid standing delegation action scope flag')
    END;
    SELECT CASE
      WHEN trim(NEW.action_id)='' OR trim(NEW.action_type)='' OR trim(NEW.action_target)=''
      THEN RAISE(ABORT, 'standing delegation evaluation requires exact action binding')
    END;
    SELECT CASE
      WHEN length(trim(NEW.facts_sha256)) != 64
      THEN RAISE(ABORT, 'standing delegation evaluation requires facts digest')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_standing_delegation_evaluations_no_update
BEFORE UPDATE ON standing_delegation_evaluations
BEGIN
    SELECT RAISE(ABORT, 'standing delegation evaluations are append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_standing_delegation_evaluations_no_delete
BEFORE DELETE ON standing_delegation_evaluations
BEGIN
    SELECT RAISE(ABORT, 'standing delegation evaluations are append-only');
END;
