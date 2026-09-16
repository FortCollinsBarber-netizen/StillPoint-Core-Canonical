-- 006_temporal_authority_hardening.sql
-- Forward-only hardening. 005 remains historical and unchanged.

-- Recorded temporal evidence is append-only through ordinary SQL operations.
CREATE TRIGGER IF NOT EXISTS trg_temporal_evidence_no_update
BEFORE UPDATE ON temporal_evidence
BEGIN
    SELECT RAISE(ABORT, 'temporal evidence is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_temporal_evidence_no_delete
BEFORE DELETE ON temporal_evidence
BEGIN
    SELECT RAISE(ABORT, 'temporal evidence is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_temporal_claims_validate_insert
BEFORE INSERT ON temporal_claims
BEGIN
    SELECT CASE
      WHEN NEW.status NOT IN ('active','historical','superseded','expired','withdrawn','review_required')
      THEN RAISE(ABORT, 'invalid temporal claim status')
    END;
    SELECT CASE
      WHEN NEW.confidence IS NOT NULL AND (NEW.confidence < 0.0 OR NEW.confidence > 1.0)
      THEN RAISE(ABORT, 'invalid temporal claim confidence')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_temporal_claims_validate_update
BEFORE UPDATE ON temporal_claims
BEGIN
    SELECT CASE
      WHEN NEW.status NOT IN ('active','historical','superseded','expired','withdrawn','review_required')
      THEN RAISE(ABORT, 'invalid temporal claim status')
    END;
    SELECT CASE
      WHEN NEW.confidence IS NOT NULL AND (NEW.confidence < 0.0 OR NEW.confidence > 1.0)
      THEN RAISE(ABORT, 'invalid temporal claim confidence')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_temporal_warrants_validate_insert
BEFORE INSERT ON temporal_warrants
BEGIN
    SELECT CASE
      WHEN NEW.status NOT IN ('active','expired','revoked','completed','superseded','review_required')
      THEN RAISE(ABORT, 'invalid temporal warrant status')
    END;
    SELECT CASE
      WHEN trim(COALESCE(NEW.issuer,'')) = ''
      THEN RAISE(ABORT, 'warrant issuer required')
    END;
    SELECT CASE
      WHEN trim(COALESCE(NEW.policy_basis,'')) = ''
      THEN RAISE(ABORT, 'warrant policy basis required')
    END;
    SELECT CASE
      WHEN NEW.status = 'active' AND NEW.valid_to IS NULL
      THEN RAISE(ABORT, 'active warrant requires finite valid_to')
    END;
    SELECT CASE
      WHEN NEW.valid_to IS NOT NULL AND julianday(NEW.valid_to) IS NULL
      THEN RAISE(ABORT, 'invalid warrant valid_to')
    END;
    SELECT CASE
      WHEN julianday(NEW.valid_from) IS NULL
      THEN RAISE(ABORT, 'invalid warrant valid_from')
    END;
    SELECT CASE
      WHEN NEW.valid_to IS NOT NULL AND julianday(NEW.valid_to) <= julianday(NEW.valid_from)
      THEN RAISE(ABORT, 'warrant valid_to must be after valid_from')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_temporal_warrants_validate_update
BEFORE UPDATE ON temporal_warrants
BEGIN
    SELECT CASE
      WHEN NEW.status NOT IN ('active','expired','revoked','completed','superseded','review_required')
      THEN RAISE(ABORT, 'invalid temporal warrant status')
    END;
    SELECT CASE
      WHEN trim(COALESCE(NEW.issuer,'')) = ''
      THEN RAISE(ABORT, 'warrant issuer required')
    END;
    SELECT CASE
      WHEN trim(COALESCE(NEW.policy_basis,'')) = ''
      THEN RAISE(ABORT, 'warrant policy basis required')
    END;
    SELECT CASE
      WHEN NEW.status = 'active' AND NEW.valid_to IS NULL
      THEN RAISE(ABORT, 'active warrant requires finite valid_to')
    END;
    SELECT CASE
      WHEN NEW.valid_to IS NOT NULL AND julianday(NEW.valid_to) IS NULL
      THEN RAISE(ABORT, 'invalid warrant valid_to')
    END;
    SELECT CASE
      WHEN julianday(NEW.valid_from) IS NULL
      THEN RAISE(ABORT, 'invalid warrant valid_from')
    END;
    SELECT CASE
      WHEN NEW.valid_to IS NOT NULL AND julianday(NEW.valid_to) <= julianday(NEW.valid_from)
      THEN RAISE(ABORT, 'warrant valid_to must be after valid_from')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_temporal_evidence_validate_insert
BEFORE INSERT ON temporal_evidence
BEGIN
    SELECT CASE
      WHEN NEW.confidence IS NOT NULL AND (NEW.confidence < 0.0 OR NEW.confidence > 1.0)
      THEN RAISE(ABORT, 'invalid temporal evidence confidence')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_temporal_releases_validate_insert
BEFORE INSERT ON temporal_releases
BEGIN
    SELECT CASE
      WHEN NEW.retains_historical_record NOT IN (0,1)
        OR NEW.restores_access NOT IN (0,1)
        OR NEW.erases_consequences NOT IN (0,1)
      THEN RAISE(ABORT, 'release flags must be boolean')
    END;
    SELECT CASE
      WHEN NEW.retains_historical_record != 1
        OR NEW.restores_access != 0
        OR NEW.erases_consequences != 0
      THEN RAISE(ABORT, 'release semantics violated')
    END;
END;
