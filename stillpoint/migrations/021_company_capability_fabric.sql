-- 021_company_capability_fabric.sql
-- Durable capability identity, office eligibility, and append-only offer/block evidence.
--
-- A capability grant is not external-action authority.
-- Provider/tool capacity is not permission to send, publish, spend, sign, delete,
-- or otherwise create an external effect. Those actions remain behind ActionRequest
-- + present warrant + dispatch evidence.

CREATE TABLE IF NOT EXISTS company_capabilities (
    capability_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    external_effect INTEGER NOT NULL DEFAULT 0,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS office_capability_grants (
    role TEXT NOT NULL,
    capability_id TEXT NOT NULL,
    status TEXT NOT NULL,
    granted_by TEXT NOT NULL,
    valid_from TEXT NOT NULL,
    review_by TEXT,
    constraints_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(role, capability_id),
    FOREIGN KEY(capability_id) REFERENCES company_capabilities(capability_id)
);

CREATE TABLE IF NOT EXISTS capability_events (
    event_id TEXT PRIMARY KEY,
    task_id TEXT,
    role TEXT NOT NULL,
    phase TEXT NOT NULL DEFAULT '',
    capability_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT '',
    occurred_at TEXT NOT NULL,
    detail_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(task_id) REFERENCES tasks(id),
    FOREIGN KEY(capability_id) REFERENCES company_capabilities(capability_id)
);
CREATE INDEX IF NOT EXISTS ix_capability_events_task
    ON capability_events(task_id, occurred_at, event_id);
CREATE INDEX IF NOT EXISTS ix_capability_events_role
    ON capability_events(role, occurred_at, event_id);

CREATE TRIGGER IF NOT EXISTS trg_company_capabilities_validate_insert
BEFORE INSERT ON company_capabilities BEGIN
  SELECT CASE WHEN trim(NEW.capability_id)='' OR trim(NEW.description)=''
    THEN RAISE(ABORT,'capability identity required') END;
  SELECT CASE WHEN NEW.kind NOT IN ('provider_tool','provider_control','internal_read','internal_compute','external_action')
    THEN RAISE(ABORT,'invalid capability kind') END;
  SELECT CASE WHEN NEW.external_effect NOT IN (0,1)
    THEN RAISE(ABORT,'invalid capability external_effect') END;
  SELECT CASE WHEN NEW.status NOT IN ('active','suspended','retired')
    THEN RAISE(ABORT,'invalid capability status') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_company_capabilities_validate_update
BEFORE UPDATE ON company_capabilities BEGIN
  SELECT CASE WHEN NEW.kind NOT IN ('provider_tool','provider_control','internal_read','internal_compute','external_action')
    THEN RAISE(ABORT,'invalid capability kind') END;
  SELECT CASE WHEN NEW.external_effect NOT IN (0,1)
    THEN RAISE(ABORT,'invalid capability external_effect') END;
  SELECT CASE WHEN NEW.status NOT IN ('active','suspended','retired')
    THEN RAISE(ABORT,'invalid capability status') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_office_capability_grants_validate_insert
BEFORE INSERT ON office_capability_grants BEGIN
  SELECT CASE WHEN trim(NEW.role)='' OR trim(NEW.capability_id)='' OR trim(NEW.granted_by)=''
    THEN RAISE(ABORT,'capability grant identity required') END;
  SELECT CASE WHEN NEW.status NOT IN ('active','suspended','revoked')
    THEN RAISE(ABORT,'invalid capability grant status') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_office_capability_grants_validate_update
BEFORE UPDATE ON office_capability_grants BEGIN
  SELECT CASE WHEN NEW.status NOT IN ('active','suspended','revoked')
    THEN RAISE(ABORT,'invalid capability grant status') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_capability_events_validate_insert
BEFORE INSERT ON capability_events BEGIN
  SELECT CASE WHEN trim(NEW.role)='' OR trim(NEW.capability_id)=''
    THEN RAISE(ABORT,'capability event identity required') END;
  SELECT CASE WHEN NEW.event_type NOT IN ('offered','blocked','grant_changed')
    THEN RAISE(ABORT,'invalid capability event type') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_capability_events_no_update
BEFORE UPDATE ON capability_events BEGIN
  SELECT RAISE(ABORT,'capability events are append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_capability_events_no_delete
BEFORE DELETE ON capability_events BEGIN
  SELECT RAISE(ABORT,'capability events are append-only');
END;
