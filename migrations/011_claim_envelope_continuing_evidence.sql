-- 011_claim_envelope_continuing_evidence.sql
-- Minimal Claim Envelope / Continuing Evidence contract.
-- This migration does not issue or broaden authority.

CREATE TABLE IF NOT EXISTS temporal_claim_envelopes (
    envelope_id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    purpose TEXT NOT NULL,
    epistemic_reach_json TEXT NOT NULL DEFAULT '{}',
    permitted_uses_json TEXT NOT NULL DEFAULT '[]',
    prohibited_uses_json TEXT NOT NULL DEFAULT '[]',
    continuation_conditions_json TEXT NOT NULL DEFAULT '[]',
    correction_routes_json TEXT NOT NULL DEFAULT '[]',
    release_conditions_json TEXT NOT NULL DEFAULT '[]',
    reentry_requirements_json TEXT NOT NULL DEFAULT '[]',
    memory_policy_json TEXT NOT NULL DEFAULT '{}',
    memory_may_reauthorize INTEGER NOT NULL DEFAULT 0,
    operational INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    supersedes_envelope_id TEXT,
    superseded_by_envelope_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(claim_id) REFERENCES temporal_claims(claim_id),
    FOREIGN KEY(supersedes_envelope_id) REFERENCES temporal_claim_envelopes(envelope_id),
    FOREIGN KEY(superseded_by_envelope_id) REFERENCES temporal_claim_envelopes(envelope_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_temporal_claim_envelopes_one_active
ON temporal_claim_envelopes(claim_id)
WHERE status='active';

CREATE INDEX IF NOT EXISTS ix_temporal_claim_envelopes_status
ON temporal_claim_envelopes(status, updated_at);

CREATE TABLE IF NOT EXISTS temporal_claim_use_events (
    use_id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL,
    envelope_id TEXT NOT NULL,
    use_kind TEXT NOT NULL,
    actor TEXT NOT NULL,
    purpose TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    warrant_id TEXT,
    action_id TEXT,
    intervention_effects_json TEXT NOT NULL DEFAULT '[]',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(claim_id) REFERENCES temporal_claims(claim_id),
    FOREIGN KEY(envelope_id) REFERENCES temporal_claim_envelopes(envelope_id),
    FOREIGN KEY(warrant_id) REFERENCES temporal_warrants(warrant_id),
    FOREIGN KEY(action_id) REFERENCES action_requests(id)
);

CREATE INDEX IF NOT EXISTS ix_temporal_claim_use_events_claim
ON temporal_claim_use_events(claim_id, occurred_at, use_id);

CREATE INDEX IF NOT EXISTS ix_temporal_claim_use_events_action
ON temporal_claim_use_events(action_id, warrant_id);

CREATE TABLE IF NOT EXISTS temporal_evidence_contexts (
    evidence_id TEXT PRIMARY KEY,
    environment TEXT NOT NULL,
    prior_use_ids_json TEXT NOT NULL DEFAULT '[]',
    system_influence_json TEXT NOT NULL DEFAULT '[]',
    recorded_at TEXT NOT NULL,
    FOREIGN KEY(evidence_id) REFERENCES temporal_evidence(evidence_id)
);

CREATE TRIGGER IF NOT EXISTS trg_temporal_claim_envelopes_validate_insert
BEFORE INSERT ON temporal_claim_envelopes
BEGIN
    SELECT CASE
      WHEN NEW.status NOT IN ('active','historical','superseded','review_required')
      THEN RAISE(ABORT, 'invalid claim envelope status')
    END;
    SELECT CASE
      WHEN NEW.operational NOT IN (0,1) OR NEW.memory_may_reauthorize NOT IN (0,1)
      THEN RAISE(ABORT, 'claim envelope boolean flags invalid')
    END;
    SELECT CASE
      WHEN NEW.memory_may_reauthorize != 0
      THEN RAISE(ABORT, 'memory cannot reauthorize operational authority')
    END;
    SELECT CASE
      WHEN trim(NEW.claim_id)='' OR trim(NEW.domain)='' OR trim(NEW.purpose)=''
      THEN RAISE(ABORT, 'claim envelope identity/domain/purpose required')
    END;
    SELECT CASE
      WHEN NEW.operational=1 AND (
        NEW.epistemic_reach_json IN ('','{}')
        OR NEW.permitted_uses_json IN ('','[]')
        OR NEW.continuation_conditions_json IN ('','[]')
        OR NEW.correction_routes_json IN ('','[]')
        OR NEW.release_conditions_json IN ('','[]')
        OR NEW.reentry_requirements_json IN ('','[]')
      )
      THEN RAISE(ABORT, 'operational claim envelope missing bounded contract')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_temporal_claim_envelopes_validate_update
BEFORE UPDATE ON temporal_claim_envelopes
BEGIN
    SELECT CASE
      WHEN NEW.status NOT IN ('active','historical','superseded','review_required')
      THEN RAISE(ABORT, 'invalid claim envelope status')
    END;
    SELECT CASE
      WHEN NEW.memory_may_reauthorize != 0
      THEN RAISE(ABORT, 'memory cannot reauthorize operational authority')
    END;
    SELECT CASE
      WHEN NEW.claim_id IS NOT OLD.claim_id
        OR NEW.domain IS NOT OLD.domain
        OR NEW.purpose IS NOT OLD.purpose
        OR NEW.epistemic_reach_json IS NOT OLD.epistemic_reach_json
        OR NEW.permitted_uses_json IS NOT OLD.permitted_uses_json
        OR NEW.prohibited_uses_json IS NOT OLD.prohibited_uses_json
        OR NEW.continuation_conditions_json IS NOT OLD.continuation_conditions_json
        OR NEW.correction_routes_json IS NOT OLD.correction_routes_json
        OR NEW.release_conditions_json IS NOT OLD.release_conditions_json
        OR NEW.reentry_requirements_json IS NOT OLD.reentry_requirements_json
        OR NEW.memory_policy_json IS NOT OLD.memory_policy_json
        OR NEW.memory_may_reauthorize IS NOT OLD.memory_may_reauthorize
        OR NEW.operational IS NOT OLD.operational
        OR NEW.supersedes_envelope_id IS NOT OLD.supersedes_envelope_id
        OR NEW.created_at IS NOT OLD.created_at
      THEN RAISE(ABORT, 'claim envelope contract fields are immutable; supersede instead')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_temporal_claim_use_events_validate_insert
BEFORE INSERT ON temporal_claim_use_events
BEGIN
    SELECT CASE
      WHEN NEW.use_kind NOT IN ('informational','operational','intervention')
      THEN RAISE(ABORT, 'invalid claim use kind')
    END;
    SELECT CASE
      WHEN trim(NEW.actor)='' OR trim(NEW.purpose)=''
      THEN RAISE(ABORT, 'claim use actor and purpose required')
    END;
    SELECT CASE
      WHEN NEW.use_kind IN ('operational','intervention')
        AND (NEW.warrant_id IS NULL OR trim(NEW.warrant_id)=''
          OR NEW.action_id IS NULL OR trim(NEW.action_id)='')
      THEN RAISE(ABORT, 'operational claim use requires bound warrant and action')
    END;
    SELECT CASE
      WHEN NEW.use_kind='intervention' AND NEW.intervention_effects_json IN ('','[]')
      THEN RAISE(ABORT, 'intervention use requires stated effects')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_temporal_claim_use_events_no_update
BEFORE UPDATE ON temporal_claim_use_events
BEGIN
    SELECT RAISE(ABORT, 'claim use history is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_temporal_claim_use_events_no_delete
BEFORE DELETE ON temporal_claim_use_events
BEGIN
    SELECT RAISE(ABORT, 'claim use history is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_temporal_evidence_contexts_validate_insert
BEFORE INSERT ON temporal_evidence_contexts
BEGIN
    SELECT CASE
      WHEN NEW.environment NOT IN ('pre_intervention','post_intervention','mixed','unknown')
      THEN RAISE(ABORT, 'invalid evidence environment')
    END;
    SELECT CASE
      WHEN NEW.environment IN ('post_intervention','mixed')
        AND NEW.prior_use_ids_json IN ('','[]')
      THEN RAISE(ABORT, 'post-intervention evidence requires prior claim-use linkage')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_temporal_evidence_contexts_no_update
BEFORE UPDATE ON temporal_evidence_contexts
BEGIN
    SELECT RAISE(ABORT, 'evidence context is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_temporal_evidence_contexts_no_delete
BEFORE DELETE ON temporal_evidence_contexts
BEGIN
    SELECT RAISE(ABORT, 'evidence context is append-only');
END;
