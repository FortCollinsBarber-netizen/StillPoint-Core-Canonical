-- Temporal authority / continuing evidence layer
-- Forward-only. Does not rewrite prior history.
-- Claims, warrants, evidence events, re-evaluation triggers, release records.

CREATE TABLE IF NOT EXISTS temporal_claims (
    claim_id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    value_json TEXT,
    domain TEXT NOT NULL,
    source TEXT NOT NULL,
    evidence_refs_json TEXT NOT NULL DEFAULT '[]',
    time_observed TEXT,
    time_asserted TEXT NOT NULL,
    effective_from TEXT,
    effective_to TEXT,
    confidence REAL,  -- NULL means unknown; never coerce to 0
    status TEXT NOT NULL,
    supersedes TEXT,
    superseded_by TEXT,
    review_conditions_json TEXT NOT NULL DEFAULT '[]',
    provenance_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_temporal_claims_subject ON temporal_claims(subject, domain, status);
CREATE INDEX IF NOT EXISTS ix_temporal_claims_status ON temporal_claims(status, updated_at);

CREATE TABLE IF NOT EXISTS temporal_warrants (
    warrant_id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    action_class TEXT NOT NULL,
    subject TEXT NOT NULL,
    target TEXT,
    claim_ids_json TEXT NOT NULL DEFAULT '[]',
    evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    issuer TEXT,
    policy_basis TEXT,
    issued_at TEXT NOT NULL,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    status TEXT NOT NULL,
    scope_json TEXT NOT NULL DEFAULT '{}',
    completion_condition TEXT,
    provenance_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    superseded_by TEXT,
    revoked_reason TEXT,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS ix_temporal_warrants_subject ON temporal_warrants(subject, domain, status);
CREATE INDEX IF NOT EXISTS ix_temporal_warrants_status ON temporal_warrants(status, valid_to);

CREATE TABLE IF NOT EXISTS temporal_evidence (
    evidence_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    subject TEXT NOT NULL,
    content_json TEXT,
    source TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    related_claim_ids_json TEXT NOT NULL DEFAULT '[]',
    related_warrant_ids_json TEXT NOT NULL DEFAULT '[]',
    sha256 TEXT,
    confidence REAL,
    tags_json TEXT NOT NULL DEFAULT '[]',
    provenance_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS ix_temporal_evidence_subject ON temporal_evidence(subject, recorded_at);

CREATE TABLE IF NOT EXISTS temporal_reevaluation_triggers (
    trigger_id TEXT PRIMARY KEY,
    prior_disposition TEXT NOT NULL,
    prior_task_id TEXT,
    prior_warrant_id TEXT,
    prior_claim_ids_json TEXT NOT NULL DEFAULT '[]',
    new_evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    reason TEXT,
    created_at TEXT NOT NULL,
    new_evaluation_id TEXT,
    provenance_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS temporal_releases (
    release_id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    prior_warrant_id TEXT,
    prior_claim_ids_json TEXT NOT NULL DEFAULT '[]',
    released_authority TEXT,
    reason TEXT,
    released_at TEXT NOT NULL,
    retains_historical_record INTEGER NOT NULL DEFAULT 1,
    restores_access INTEGER NOT NULL DEFAULT 0,
    erases_consequences INTEGER NOT NULL DEFAULT 0,
    provenance_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS ix_temporal_releases_subject ON temporal_releases(subject, released_at);
