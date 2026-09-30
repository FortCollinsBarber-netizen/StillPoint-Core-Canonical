-- 024_acquired_resource_quarantine.sql
-- Dynamically acquired resources are evidence/custody, never implicit authority.
-- Lifecycle: quarantined -> resolved -> activated -> consumed|expired.
-- Activation requires a separately issued temporal warrant; terminal states never revive.

CREATE TABLE IF NOT EXISTS acquired_resources (
    resource_id TEXT PRIMARY KEY,
    owner_role TEXT NOT NULL,
    kind TEXT NOT NULL,
    status TEXT NOT NULL,
    discovered_capabilities_json TEXT NOT NULL DEFAULT '[]',
    resolved_capabilities_json TEXT NOT NULL DEFAULT '[]',
    authorized_capabilities_json TEXT NOT NULL DEFAULT '[]',
    parent_capabilities_json TEXT NOT NULL DEFAULT '[]',
    activation_warrant_id TEXT,
    one_shot INTEGER NOT NULL DEFAULT 0,
    acquired_at TEXT NOT NULL,
    resolved_at TEXT,
    activated_at TEXT,
    consumed_at TEXT,
    expired_at TEXT,
    provenance_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL,
    FOREIGN KEY(activation_warrant_id) REFERENCES temporal_warrants(warrant_id)
);
CREATE INDEX IF NOT EXISTS ix_acquired_resources_owner_status
ON acquired_resources(owner_role,status,updated_at);

CREATE TABLE IF NOT EXISTS acquired_resource_events (
    event_id TEXT PRIMARY KEY,
    resource_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    detail_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(resource_id) REFERENCES acquired_resources(resource_id)
);
CREATE INDEX IF NOT EXISTS ix_acquired_resource_events_resource
ON acquired_resource_events(resource_id,occurred_at,event_id);

CREATE TRIGGER IF NOT EXISTS trg_acquired_resources_validate_insert
BEFORE INSERT ON acquired_resources BEGIN
  SELECT CASE WHEN trim(NEW.resource_id)='' OR trim(NEW.owner_role)='' OR trim(NEW.kind)=''
    THEN RAISE(ABORT,'acquired resource identity fields required') END;
  SELECT CASE WHEN NEW.status<>'quarantined'
    THEN RAISE(ABORT,'acquired resource must enter quarantine') END;
  SELECT CASE WHEN NEW.one_shot NOT IN (0,1)
    THEN RAISE(ABORT,'invalid acquired resource one_shot flag') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_acquired_resources_validate_update
BEFORE UPDATE ON acquired_resources BEGIN
  SELECT CASE WHEN NEW.resource_id<>OLD.resource_id OR NEW.owner_role<>OLD.owner_role OR NEW.kind<>OLD.kind
    THEN RAISE(ABORT,'acquired resource identity is immutable') END;
  SELECT CASE WHEN NEW.status NOT IN ('quarantined','resolved','activated','consumed','expired')
    THEN RAISE(ABORT,'invalid acquired resource status') END;
  SELECT CASE WHEN NEW.one_shot NOT IN (0,1)
    THEN RAISE(ABORT,'invalid acquired resource one_shot flag') END;
  SELECT CASE WHEN OLD.status='quarantined' AND NEW.status NOT IN ('quarantined','resolved','expired')
    THEN RAISE(ABORT,'invalid acquired resource transition') END;
  SELECT CASE WHEN OLD.status='resolved' AND NEW.status NOT IN ('resolved','activated','expired')
    THEN RAISE(ABORT,'invalid acquired resource transition') END;
  SELECT CASE WHEN OLD.status='activated' AND NEW.status NOT IN ('activated','consumed','expired')
    THEN RAISE(ABORT,'invalid acquired resource transition') END;
  SELECT CASE WHEN OLD.status IN ('consumed','expired') AND NEW.status<>OLD.status
    THEN RAISE(ABORT,'terminal acquired resource cannot revive') END;
  SELECT CASE WHEN OLD.status='activated' AND (
      NEW.activation_warrant_id<>OLD.activation_warrant_id OR
      NEW.authorized_capabilities_json<>OLD.authorized_capabilities_json OR
      NEW.parent_capabilities_json<>OLD.parent_capabilities_json)
    THEN RAISE(ABORT,'activated authority binding is immutable') END;
  SELECT CASE WHEN NEW.status IN ('activated','consumed') AND
      (NEW.activation_warrant_id IS NULL OR trim(NEW.activation_warrant_id)='')
    THEN RAISE(ABORT,'activated resource requires warrant') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_acquired_resource_events_validate_insert
BEFORE INSERT ON acquired_resource_events BEGIN
  SELECT CASE WHEN NEW.event_type NOT IN
    ('acquired','resolved','activated','use_checked','use_reserved','consumed','expired','blocked')
    THEN RAISE(ABORT,'invalid acquired resource event') END;
END;
CREATE TRIGGER IF NOT EXISTS trg_acquired_resource_events_no_update
BEFORE UPDATE ON acquired_resource_events BEGIN
  SELECT RAISE(ABORT,'acquired resource events are append-only');
END;
CREATE TRIGGER IF NOT EXISTS trg_acquired_resource_events_no_delete
BEFORE DELETE ON acquired_resource_events BEGIN
  SELECT RAISE(ABORT,'acquired resource events are append-only');
END;
