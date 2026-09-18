-- 022_stage3_audit_closure.sql
-- Make budget accounting describe observed reality instead of tool availability,
-- and begin cryptographic custody for migration bytes.
--
-- Historical note:
-- task_usage.tool_calls was populated from len(tools), so it means "tool offers"
-- for schema <=21. Preserve it as legacy evidence; do not reinterpret it.

ALTER TABLE task_usage ADD COLUMN tool_offers INTEGER NOT NULL DEFAULT 0;
ALTER TABLE task_usage ADD COLUMN tool_invocations INTEGER NOT NULL DEFAULT 0;
ALTER TABLE task_usage ADD COLUMN tool_invocation_unknown_calls INTEGER NOT NULL DEFAULT 0;
ALTER TABLE task_usage ADD COLUMN cost_unknown_calls INTEGER NOT NULL DEFAULT 0;

UPDATE task_usage
SET tool_offers = tool_calls,
    tool_invocation_unknown_calls = CASE
        WHEN tool_calls > 0 THEN model_calls
        ELSE 0
    END,
    cost_unknown_calls = model_calls;

CREATE TABLE IF NOT EXISTS schema_migration_custody (
    version INTEGER PRIMARY KEY,
    sha256 TEXT NOT NULL,
    migration_name TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    custody_source TEXT NOT NULL,
    FOREIGN KEY(version) REFERENCES schema_migrations(version)
);

CREATE TRIGGER IF NOT EXISTS trg_schema_migration_custody_validate_insert
BEFORE INSERT ON schema_migration_custody BEGIN
  SELECT CASE WHEN length(NEW.sha256) != 64
    THEN RAISE(ABORT,'migration sha256 required') END;
  SELECT CASE WHEN NEW.custody_source NOT IN ('applied_exact','canonical_backfill')
    THEN RAISE(ABORT,'invalid migration custody source') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_schema_migration_custody_no_update
BEFORE UPDATE ON schema_migration_custody BEGIN
  SELECT RAISE(ABORT,'migration custody is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_schema_migration_custody_no_delete
BEFORE DELETE ON schema_migration_custody BEGIN
  SELECT RAISE(ABORT,'migration custody is append-only');
END;
