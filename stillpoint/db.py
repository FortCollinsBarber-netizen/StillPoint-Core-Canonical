from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


_MIGRATION_RE = re.compile(r"^(\d{3})_.*\.sql$")
TASK_UPDATE_COLUMNS = frozenset(
    {
        "updated_at",
        "goal",
        "project",
        "status",
        "plan_json",
        "final_output",
        "review_output",
        "approval_reason",
        "error",
        "input_fingerprint",
    }
)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_migrations_dir() -> Path:
    """Return the canonical migration directory for a checkout or installed package.

    In a source checkout the top-level ``migrations`` directory is authoritative.
    Packaged releases include a verified mirror under ``stillpoint/migrations``.
    """

    checkout = Path(__file__).resolve().parents[1] / "migrations"
    if checkout.is_dir():
        return checkout
    packaged = Path(__file__).resolve().parent / "migrations"
    if packaged.is_dir():
        return packaged
    return checkout


MIGRATIONS_DIR = _default_migrations_dir()


def _migration_files(directory: Path | None = None) -> list[tuple[int, Path]]:
    root = Path(directory or MIGRATIONS_DIR)
    items: list[tuple[int, Path]] = []
    for path in root.glob("*.sql"):
        match = _MIGRATION_RE.match(path.name)
        if match:
            items.append((int(match.group(1)), path))
    items.sort(key=lambda item: item[0])
    return items


def _sql_statements(script: str) -> Iterable[str]:
    """Yield complete SQL statements without giving ``executescript`` transaction control."""

    pending = ""
    for line in script.splitlines(keepends=True):
        pending += line
        if sqlite3.complete_statement(pending):
            statement = pending.strip()
            pending = ""
            if statement:
                yield statement
    if pending.strip():
        raise RuntimeError("migration contains incomplete SQL")


def _migration_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _custody_table_exists(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master "
        "WHERE type='table' AND name='schema_migration_custody'"
    ).fetchone()
    return bool(row)


def _sync_migration_custody(
    conn: sqlite3.Connection,
    migrations: list[tuple[int, Path]],
    *,
    applied_now: set[int],
) -> None:
    """Verify known migration hashes and record missing custody rows.

    Rows for migrations applied in this process are exact execution custody.
    Older rows discovered after custody support was introduced are explicitly
    labeled canonical_backfill; they attest current canonical bytes, not
    historical execution bytes.
    """

    if not _custody_table_exists(conn):
        return

    applied = {
        int(row[0])
        for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
    }
    existing = {
        int(row["version"]): (str(row["sha256"]), str(row["migration_name"]))
        for row in conn.execute(
            "SELECT version,sha256,migration_name FROM schema_migration_custody"
        ).fetchall()
    }

    for version, path in migrations:
        if version not in applied:
            continue
        digest = _migration_sha256(path)
        name = path.name
        prior = existing.get(version)
        if prior:
            if prior != (digest, name):
                raise RuntimeError(
                    f"migration custody mismatch for version {version}: "
                    f"recorded={prior[1]}:{prior[0]} current={name}:{digest}"
                )
            continue
        source = "applied_exact" if version in applied_now else "canonical_backfill"
        conn.execute(
            """INSERT INTO schema_migration_custody(
               version,sha256,migration_name,recorded_at,custody_source
               ) VALUES(?,?,?,?,?)""",
            (version, digest, name, utcnow(), source),
        )


class CompanyDB:
    def __init__(
        self,
        path: Path,
        *,
        migrations_dir: Path | None = None,
        check_same_thread: bool = True,
    ):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.migrations_dir = Path(migrations_dir or MIGRATIONS_DIR)
        self.check_same_thread = bool(check_same_thread)
        self.conn: sqlite3.Connection | None = sqlite3.connect(
            self.path,
            check_same_thread=self.check_same_thread,
        )
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._closed = False
        self._migrate()

    def _connection(self) -> sqlite3.Connection:
        if self._closed or self.conn is None:
            raise RuntimeError("database is closed")
        return self.conn

    def _migrate(self) -> None:
        conn = self._connection()
        migrations = _migration_files(self.migrations_dir)
        if not migrations:
            raise RuntimeError(f"no migration files found in {self.migrations_dir}")
        versions = [version for version, _ in migrations]
        if versions != list(range(versions[0], versions[-1] + 1)) or versions[0] != 1:
            raise RuntimeError(f"migration versions must be contiguous from 1: {versions}")

        # Bootstrap only. The migration decision itself is made after acquiring
        # the write reservation so concurrent startup processes cannot both
        # decide that the same migration is pending.
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        conn.commit()

        latest = migrations[-1][0]
        applied_now: set[int] = set()
        try:
            conn.execute("BEGIN IMMEDIATE")
            current = (
                conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
                or 0
            )
            if current > latest:
                raise RuntimeError(
                    f"database schema version {current} is newer than runtime {latest}"
                )

            # If custody already exists, verify it before applying anything new.
            _sync_migration_custody(conn, migrations, applied_now=applied_now)

            for version, path in migrations:
                if version <= current:
                    continue
                if version != current + 1:
                    raise RuntimeError(
                        f"migration sequence gap: current={current} next={version}"
                    )
                script = path.read_text(encoding="utf-8")
                for statement in _sql_statements(script):
                    conn.execute(statement)
                conn.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES(?, ?)",
                    (version, utcnow()),
                )
                applied_now.add(version)
                current = version

                # Migration 22 creates the custody table. Recording here keeps
                # the current migration hash in the same transaction as the SQL
                # bytes that produced the schema.
                _sync_migration_custody(
                    conn,
                    migrations,
                    applied_now=applied_now,
                )

            # Also backfill/verify custody when no migration was pending.
            _sync_migration_custody(conn, migrations, applied_now=applied_now)
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    @property
    def schema_version(self) -> int:
        row = self._connection().execute("SELECT MAX(version) FROM schema_migrations").fetchone()
        return int(row[0] or 0)

    def close(self) -> None:
        if self._closed:
            return
        conn = self.conn
        self.conn = None
        self._closed = True
        if conn is not None:
            conn.close()

    def __enter__(self) -> "CompanyDB":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def __del__(self):
        # Best-effort cleanup only. Production code should close explicitly or use a context manager.
        try:
            self.close()
        except Exception:
            pass

    def create_task(self, goal: str, project: str | None = None) -> str:
        task_id = uuid.uuid4().hex[:12]
        now = utcnow()
        conn = self._connection()
        conn.execute(
            "INSERT INTO tasks(id,created_at,updated_at,goal,project,status) VALUES(?,?,?,?,?,?)",
            (task_id, now, now, goal, project, "new"),
        )
        conn.commit()
        return task_id

    def update_task(self, task_id: str, **fields: Any) -> None:
        if not fields:
            return
        bad = [key for key in fields if key not in TASK_UPDATE_COLUMNS]
        if bad:
            raise ValueError(f"disallowed task columns: {bad}")
        fields["updated_at"] = utcnow()
        cols = ", ".join(f"{key}=?" for key in fields)
        conn = self._connection()
        conn.execute(f"UPDATE tasks SET {cols} WHERE id=?", [*fields.values(), task_id])
        conn.commit()

    def set_plan(self, task_id: str, plan: dict[str, Any]) -> None:
        self.update_task(task_id, plan_json=json.dumps(plan, ensure_ascii=False), status="running")

    def add_plan_revision(
        self,
        task_id: str,
        instruction_fingerprint: str,
        authority_revision: str,
        plan: dict[str, Any],
    ) -> str:
        revision_id = uuid.uuid4().hex[:12]
        conn = self._connection()
        conn.execute(
            "INSERT INTO plan_revisions(id,task_id,created_at,instruction_fingerprint,authority_revision,plan_json) "
            "VALUES(?,?,?,?,?,?)",
            (
                revision_id,
                task_id,
                utcnow(),
                instruction_fingerprint,
                authority_revision,
                json.dumps(plan, ensure_ascii=False),
            ),
        )
        conn.commit()
        return revision_id

    def list_plan_revisions(self, task_id: str) -> list[dict[str, Any]]:
        rows = self._connection().execute(
            "SELECT * FROM plan_revisions WHERE task_id=? ORDER BY created_at,id", (task_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def add_resume_instruction(
        self,
        task_id: str,
        instruction: str,
        instruction_fingerprint: str,
        authority_revision: str,
        plan_revision_id: str,
    ) -> str:
        instruction_id = uuid.uuid4().hex[:12]
        conn = self._connection()
        conn.execute(
            "INSERT INTO resume_instructions(id,task_id,created_at,instruction,instruction_fingerprint,authority_revision,plan_revision_id) "
            "VALUES(?,?,?,?,?,?,?)",
            (
                instruction_id,
                task_id,
                utcnow(),
                instruction,
                instruction_fingerprint,
                authority_revision,
                plan_revision_id,
            ),
        )
        conn.commit()
        return instruction_id

    def list_resume_instructions(self, task_id: str) -> list[dict[str, Any]]:
        rows = self._connection().execute(
            "SELECT * FROM resume_instructions WHERE task_id=? ORDER BY created_at,id", (task_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def add_run(
        self,
        task_id: str,
        agent_id: str,
        phase: str,
        output: str,
        model: str = "",
        input_summary: str = "",
        citations: list[str] | None = None,
        provider_response_id: str = "",
        usage: dict | None = None,
        stage_key: str = "",
    ) -> str:
        run_id = uuid.uuid4().hex[:12]
        conn = self._connection()
        try:
            conn.execute(
                """INSERT INTO agent_runs
                (id,task_id,created_at,agent_id,phase,model,input_summary,output,citations_json,
                 provider_response_id,usage_json,stage_key)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    run_id,
                    task_id,
                    utcnow(),
                    agent_id,
                    phase,
                    model,
                    input_summary,
                    output,
                    json.dumps(citations or [], ensure_ascii=False),
                    provider_response_id,
                    json.dumps(usage or {}, ensure_ascii=False),
                    stage_key,
                ),
            )
        except sqlite3.IntegrityError as exc:
            if stage_key and "agent_runs.stage_key" in str(exc):
                row = conn.execute("SELECT id FROM agent_runs WHERE stage_key=?", (stage_key,)).fetchone()
                if row:
                    return str(row[0])
            raise
        conn.commit()
        return run_id

    def get_run_by_stage_key(self, key: str) -> dict[str, Any] | None:
        row = self._connection().execute("SELECT * FROM agent_runs WHERE stage_key=?", (key,)).fetchone()
        return dict(row) if row else None

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        row = self._connection().execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return dict(row) if row else None

    def list_tasks(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._connection().execute(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]

    def list_runs(self, task_id: str) -> list[dict[str, Any]]:
        rows = self._connection().execute(
            "SELECT * FROM agent_runs WHERE task_id=? ORDER BY created_at,id", (task_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def add_approval(self, task_id: str, decision: str, note: str = "") -> str:
        approval_id = uuid.uuid4().hex[:12]
        conn = self._connection()
        conn.execute(
            "INSERT INTO approvals(id,task_id,created_at,decision,note) VALUES(?,?,?,?,?)",
            (approval_id, task_id, utcnow(), decision, note),
        )
        conn.commit()
        return approval_id

    def add_artifact(
        self,
        *,
        task_id: str,
        kind: str,
        name: str,
        sha256: str,
        produced_by_run_id: str,
        phase: str,
        project: str | None = None,
        version: int | None = None,
        supersedes: str | None = None,
        body_path: str | None = None,
        action_id: str | None = None,
    ) -> str:
        conn = self._connection()
        prior = conn.execute(
            "SELECT id,version FROM artifacts WHERE task_id=? AND kind=? "
            "ORDER BY version DESC,created_at DESC LIMIT 1",
            (task_id, kind),
        ).fetchone()
        if version is None:
            version = int(prior["version"] + 1) if prior else 1
        if supersedes is None and prior:
            supersedes = str(prior["id"])
        artifact_id = uuid.uuid4().hex[:12]
        conn.execute(
            """INSERT INTO artifacts
            (id,task_id,project,kind,name,sha256,produced_by_run_id,phase,version,supersedes,body_path,action_id,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                artifact_id,
                task_id,
                project,
                kind,
                name,
                sha256,
                produced_by_run_id,
                phase,
                version,
                supersedes,
                body_path,
                action_id,
                utcnow(),
            ),
        )
        conn.commit()
        return artifact_id

    def list_artifacts(self, task_id: str) -> list[dict[str, Any]]:
        rows = self._connection().execute(
            "SELECT * FROM artifacts WHERE task_id=? ORDER BY created_at,id", (task_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def get_artifact(self, artifact_id: str) -> dict[str, Any] | None:
        row = self._connection().execute(
            "SELECT * FROM artifacts WHERE id=?", (artifact_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        row = self._connection().execute(
            "SELECT * FROM agent_runs WHERE id=?", (run_id,)
        ).fetchone()
        return dict(row) if row else None

    def add_task_file(
        self,
        task_id: str,
        path: str,
        name: str,
        sha256: str,
        original_name: str | None = None,
        media_type: str | None = None,
        size_bytes: int | None = None,
    ) -> str:
        file_id = uuid.uuid4().hex[:12]
        conn = self._connection()
        conn.execute(
            "INSERT INTO task_files(id,task_id,path,name,sha256,created_at,original_name,media_type,size_bytes) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (
                file_id,
                task_id,
                path,
                name,
                sha256,
                utcnow(),
                original_name or name,
                media_type,
                size_bytes,
            ),
        )
        conn.commit()
        return file_id

    def list_task_files(self, task_id: str) -> list[dict[str, Any]]:
        rows = self._connection().execute(
            "SELECT * FROM task_files WHERE task_id=? ORDER BY created_at,id", (task_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def set_memory(
        self,
        key: str,
        value: str,
        scope: str = "company",
        source: str = "CEO",
        confidence: str = "verified",
        task_id: str | None = None,
    ) -> None:
        conn = self._connection()
        conn.execute(
            """INSERT INTO memory(scope,key,value,source,updated_at,confidence,task_id)
            VALUES(?,?,?,?,?,?,?)
            ON CONFLICT(scope,key) DO UPDATE SET
              value=excluded.value,
              source=excluded.source,
              updated_at=excluded.updated_at,
              confidence=excluded.confidence,
              task_id=excluded.task_id""",
            (scope, key, value, source, utcnow(), confidence, task_id),
        )
        conn.commit()

    def get_memory(self, scopes: list[str] | None = None) -> list[dict[str, Any]]:
        conn = self._connection()
        if scopes:
            placeholders = ",".join("?" for _ in scopes)
            rows = conn.execute(
                f"SELECT * FROM memory WHERE scope IN ({placeholders}) ORDER BY scope,key", scopes
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM memory ORDER BY scope,key").fetchall()
        return [dict(row) for row in rows]

    def add_action_request(self, request) -> str:
        conn = self._connection()
        now = utcnow()
        conn.execute(
            """INSERT INTO action_requests
            (id,task_id,created_at,updated_at,action_type,target,scope_json,artifact_refs_json,
             approval_required,approval_id,expires_at,issued_at,idempotency_key,success_criteria_json,
             click_irreversible,authority_revision,status)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                request.action_id,
                request.task_id,
                now,
                now,
                request.action_type,
                request.target,
                json.dumps(request.scope, ensure_ascii=False),
                json.dumps([asdict(item) for item in request.artifact_refs], ensure_ascii=False),
                1 if request.approval_required else 0,
                request.approval_id,
                request.expires_at,
                request.issued_at,
                request.idempotency_key,
                json.dumps(request.success_criteria, ensure_ascii=False),
                1 if request.click_irreversible else 0,
                request.authority_revision,
                "waiting_approval" if request.approval_required else "ready_for_action",
            ),
        )
        conn.commit()
        return request.action_id

    def get_action_request(self, action_id: str) -> dict[str, Any] | None:
        row = self._connection().execute(
            "SELECT * FROM action_requests WHERE id=?", (action_id,)
        ).fetchone()
        return dict(row) if row else None

    def find_action_request_by_idempotency(self, key: str) -> dict[str, Any] | None:
        row = self._connection().execute(
            "SELECT * FROM action_requests WHERE idempotency_key=?", (key,)
        ).fetchone()
        return dict(row) if row else None

    def list_action_requests(self, task_id: str) -> list[dict[str, Any]]:
        rows = self._connection().execute(
            "SELECT * FROM action_requests WHERE task_id=? ORDER BY created_at,id", (task_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def update_action_request_status(self, action_id: str, status: str) -> None:
        conn = self._connection()
        conn.execute(
            "UPDATE action_requests SET status=?,updated_at=? WHERE id=?",
            (status, utcnow(), action_id),
        )
        conn.commit()

    def mark_action_stale(self, action_id: str, reason: str = "stale authorization") -> None:
        # The schema intentionally stores status, not free-form stale reasons. The caller's
        # exception/event supplies the human-readable reason while persistence stays normalized.
        del reason
        self.update_action_request_status(action_id, "stale")

    def invalidate_task_action_authority(
        self,
        task_id: str,
        *,
        reason: str = "plan repaired",
    ) -> list[str]:
        """Atomically stale unspent action requests and revoke their active warrants.

        A repaired plan must never inherit authority merely because an earlier
        plan reached approval. Completed/uncertain dispatch history is left
        untouched; only authority that has not crossed the external boundary is
        withdrawn.
        """
        conn = self._connection()
        invalidated: list[str] = []
        now = utcnow()
        try:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute(
                """SELECT id,warrant_id,status FROM action_requests
                   WHERE task_id=? AND status IN ('waiting_approval','ready_for_action')""",
                (task_id,),
            ).fetchall()
            for row in rows:
                action_id = str(row["id"])
                invalidated.append(action_id)
                conn.execute(
                    "UPDATE action_requests SET status='stale',updated_at=? WHERE id=?",
                    (now, action_id),
                )
                warrant_id = row["warrant_id"]
                if warrant_id:
                    conn.execute(
                        """UPDATE temporal_warrants
                           SET status='revoked',revoked_reason=?,updated_at=?
                           WHERE warrant_id=? AND status='active'""",
                        (reason, now, warrant_id),
                    )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        return invalidated

    def bind_action_approval(self, action_id: str, approval_id: str) -> None:
        conn = self._connection()
        row = conn.execute(
            "SELECT task_id,artifact_refs_json FROM action_requests WHERE id=?", (action_id,)
        ).fetchone()
        if not row:
            raise KeyError(action_id)
        approval = conn.execute(
            "SELECT task_id,decision FROM approvals WHERE id=?", (approval_id,)
        ).fetchone()
        if not approval:
            raise KeyError(approval_id)
        if approval["task_id"] != row["task_id"]:
            raise ValueError("approval belongs to a different task")
        if approval["decision"] != "approved":
            raise ValueError("approval record is not approved")
        refs = json.loads(row["artifact_refs_json"])
        hashes = [item.get("sha256") for item in refs]
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "INSERT INTO action_approvals(action_id,approval_id,bound_at,artifact_hashes_json) VALUES(?,?,?,?)",
                (action_id, approval_id, utcnow(), json.dumps(hashes, ensure_ascii=False)),
            )
            # Patch 004: approval bind alone does not grant ready_for_action;
            # warrant binding via authorize_actions_atomically is required.
            conn.execute(
                "UPDATE action_requests SET approval_id=?,updated_at=? WHERE id=?",
                (approval_id, utcnow(), action_id),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def has_action_approval(self, action_id: str, approval_id: str | None) -> bool:
        if not approval_id:
            return False
        row = self._connection().execute(
            "SELECT 1 FROM action_approvals WHERE action_id=? AND approval_id=?",
            (action_id, approval_id),
        ).fetchone()
        return bool(row)

    def add_action_result(self, result) -> str:
        result_id = uuid.uuid4().hex[:12]
        conn = self._connection()
        conn.execute(
            "INSERT INTO action_results(id,action_id,created_at,status,evidence_json,external_id,error,adapter) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (
                result_id,
                result.action_id,
                utcnow(),
                result.status,
                json.dumps([asdict(item) for item in result.evidence], ensure_ascii=False),
                result.external_id,
                result.error,
                result.adapter,
            ),
        )
        conn.commit()
        return result_id

    def list_action_results(self, action_id: str) -> list[dict[str, Any]]:
        rows = self._connection().execute(
            "SELECT * FROM action_results WHERE action_id=? ORDER BY created_at,id", (action_id,)
        ).fetchall()
        return [dict(row) for row in rows]


    # ---- Temporal action-warrant gate (Patch 002) ----

    def insert_temporal_warrant(self, warrant) -> str:
        """Alias for add_temporal_warrant (Patch 002 naming)."""
        return self.add_temporal_warrant(warrant)

    def bind_action_warrant(self, action_id: str, warrant_id: str) -> None:
        conn = self._connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            action = conn.execute(
                "SELECT warrant_id FROM action_requests WHERE id=?", (action_id,)
            ).fetchone()
            if not action:
                raise KeyError(action_id)
            if action["warrant_id"] and action["warrant_id"] != warrant_id:
                raise RuntimeError("action already bound to a different warrant")
            warrant = conn.execute(
                "SELECT status FROM temporal_warrants WHERE warrant_id=?", (warrant_id,)
            ).fetchone()
            if not warrant or warrant["status"] != "active":
                raise RuntimeError("cannot bind missing or non-active warrant")
            conn.execute(
                "UPDATE action_requests SET warrant_id=?,warrant_bound_at=?,updated_at=? WHERE id=?",
                (warrant_id, utcnow(), utcnow(), action_id),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def count_warrant_consumptions(self, warrant_id: str) -> int:
        # null_probe dispositions are dry-run/null adapter probes and do not consume max_actions
        row = self._connection().execute(
            "SELECT COUNT(*) FROM action_warrant_consumptions WHERE warrant_id=? AND disposition != 'null_probe'",
            (warrant_id,),
        ).fetchone()
        return int(row[0] or 0)

    def reserve_warrant_for_action(
        self,
        *,
        action_id: str,
        warrant_id: str,
        authority_revision: str,
        approval_id: str | None,
        artifact_hashes: list[str],
    ) -> None:
        conn = self._connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            action = conn.execute(
                """SELECT warrant_id,authority_revision,approval_id,task_id,
                          action_type,status
                   FROM action_requests WHERE id=?""",
                (action_id,),
            ).fetchone()
            if not action:
                raise KeyError(action_id)
            if action["warrant_id"] != warrant_id:
                raise RuntimeError("action/warrant binding mismatch")
            if action["authority_revision"] != authority_revision:
                raise RuntimeError("authority revision changed")
            if approval_id and action["approval_id"] != approval_id:
                raise RuntimeError("approval binding changed")
            if action["status"] != "ready_for_action":
                raise RuntimeError(
                    f"action is not dispatchable from status={action['status']}"
                )
            task = conn.execute(
                "SELECT plan_json FROM tasks WHERE id=?",
                (action["task_id"],),
            ).fetchone()
            if not task or not task["plan_json"]:
                raise RuntimeError("current task plan is unavailable")
            try:
                current_plan = json.loads(task["plan_json"])
            except Exception as exc:
                raise RuntimeError("current task plan is invalid") from exc
            if current_plan.get("authority_revision") != authority_revision:
                raise RuntimeError("action authority revision is no longer current")
            if action["action_type"] not in set(current_plan.get("restricted_actions") or []):
                raise RuntimeError("action intent is no longer present in current plan")
            # Replace a prior null_probe reservation so a real dispatch can proceed
            conn.execute(
                "DELETE FROM action_warrant_consumptions WHERE action_id=? AND disposition='null_probe'",
                (action_id,),
            )
            conn.execute(
                """INSERT INTO action_warrant_consumptions
                (action_id,warrant_id,consumed_at,authority_revision,approval_id,
                 artifact_hashes_json,disposition)
                VALUES(?,?,?,?,?,?,?)""",
                (
                    action_id, warrant_id, utcnow(), authority_revision, approval_id,
                    json.dumps(artifact_hashes, ensure_ascii=False), "reserved",
                ),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def set_warrant_consumption_disposition(self, action_id: str, disposition: str) -> None:
        if disposition not in {"reserved", "completed", "failed", "uncertain", "null_probe", "dispatching", "reconciled_effect", "reconciled_no_effect"}:
            raise ValueError(f"invalid warrant consumption disposition: {disposition}")
        conn = self._connection()
        conn.execute(
            "UPDATE action_warrant_consumptions SET disposition=? WHERE action_id=?",
            (disposition, action_id),
        )
        conn.commit()

    def complete_temporal_warrant(self, warrant_id: str) -> None:
        conn = self._connection()
        conn.execute(
            "UPDATE temporal_warrants SET status='completed',completed_at=?,updated_at=? "
            "WHERE warrant_id=? AND status='active'",
            (utcnow(), utcnow(), warrant_id),
        )
        conn.commit()


    # ---- Durable dispatch / reconciliation (Patch 003) ----

    def get_action_dispatch(self, action_id: str) -> dict[str, Any] | None:
        row = self._connection().execute(
            "SELECT * FROM action_dispatches WHERE action_id=?", (action_id,)
        ).fetchone()
        return dict(row) if row else None

    def begin_external_dispatch(
        self,
        *,
        action_id: str,
        warrant_id: str,
        adapter: str,
        idempotency_key: str,
        authority_revision: str,
        approval_id: str | None,
        artifact_hashes: list[str],
    ) -> dict[str, Any]:
        """Cross the durable external-dispatch boundary exactly once.

        The transaction records the chosen adapter and consumes the one-use
        warrant before the adapter is invoked. If this transaction commits,
        automatic retry of the same ActionRequest is forbidden.
        """
        from .dispatch import is_probe_adapter_name, require_no_prior_real_dispatch

        if is_probe_adapter_name(adapter):
            raise ValueError("probe adapter must not cross external dispatch boundary")

        conn = self._connection()
        try:
            conn.execute("BEGIN IMMEDIATE")

            existing = conn.execute(
                "SELECT * FROM action_dispatches WHERE action_id=?", (action_id,)
            ).fetchone()
            if existing:
                require_no_prior_real_dispatch(dict(existing))

            action = conn.execute(
                """SELECT id,task_id,warrant_id,idempotency_key,authority_revision,
                          approval_id,status,action_type
                   FROM action_requests WHERE id=?""",
                (action_id,),
            ).fetchone()
            if not action:
                raise KeyError(action_id)
            if action["warrant_id"] != warrant_id:
                raise RuntimeError("action/warrant binding mismatch")
            if action["idempotency_key"] != idempotency_key:
                raise RuntimeError("action idempotency key changed")
            if action["authority_revision"] != authority_revision:
                raise RuntimeError("authority revision changed")
            if (action["approval_id"] or "") != (approval_id or ""):
                raise RuntimeError("approval binding changed")
            if action["status"] != "ready_for_action":
                raise RuntimeError(
                    f"action is not dispatchable from status={action['status']}"
                )
            task = conn.execute(
                "SELECT plan_json FROM tasks WHERE id=?",
                (action["task_id"],),
            ).fetchone()
            if not task or not task["plan_json"]:
                raise RuntimeError("current task plan is unavailable")
            try:
                current_plan = json.loads(task["plan_json"])
            except Exception as exc:
                raise RuntimeError("current task plan is invalid") from exc
            if current_plan.get("authority_revision") != authority_revision:
                raise RuntimeError("action authority revision is no longer current")
            if action["action_type"] not in set(current_plan.get("restricted_actions") or []):
                raise RuntimeError("action intent is no longer present in current plan")

            warrant = conn.execute(
                "SELECT status FROM temporal_warrants WHERE warrant_id=?",
                (warrant_id,),
            ).fetchone()
            if not warrant:
                raise KeyError(warrant_id)
            if warrant["status"] != "active":
                raise RuntimeError("bound warrant is no longer active")

            consumption = conn.execute(
                "SELECT disposition FROM action_warrant_consumptions WHERE action_id=?",
                (action_id,),
            ).fetchone()
            if not consumption:
                raise RuntimeError(
                    "warrant use must be durably reserved before external dispatch"
                )
            if consumption["disposition"] not in {"reserved", "null_probe"}:
                raise RuntimeError(
                    f"warrant reservation is not dispatchable: "
                    f"{consumption['disposition']}"
                )

            now = utcnow()
            conn.execute(
                """INSERT INTO action_dispatches
                (action_id,warrant_id,task_id,adapter,idempotency_key,
                 authority_revision,approval_id,artifact_hashes_json,state,
                 created_at,started_at,result_evidence_json,
                 reconciliation_evidence_json)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    action_id,
                    warrant_id,
                    action["task_id"],
                    adapter,
                    idempotency_key,
                    authority_revision,
                    approval_id,
                    json.dumps(artifact_hashes, ensure_ascii=False),
                    "dispatching",
                    now,
                    now,
                    "[]",
                    "[]",
                ),
            )
            conn.execute(
                "UPDATE action_requests SET status='dispatching',updated_at=? WHERE id=?",
                (now, action_id),
            )
            conn.execute(
                "UPDATE action_warrant_consumptions "
                "SET disposition='dispatching' WHERE action_id=?",
                (action_id,),
            )

            # A one-use authorization is spent when real external dispatch begins,
            # not when we later learn the outcome.
            conn.execute(
                """UPDATE temporal_warrants
                   SET status='completed',completed_at=?,updated_at=?
                   WHERE warrant_id=? AND status='active'""",
                (now, now, warrant_id),
            )
            if conn.total_changes < 1:
                raise RuntimeError("failed to consume active warrant")

            conn.commit()
            return self.get_action_dispatch(action_id)
        except Exception:
            conn.rollback()
            raise

    def mark_external_dispatch_uncertain(self, action_id: str, error: str = "") -> None:
        conn = self._connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT task_id,state FROM action_dispatches WHERE action_id=?",
                (action_id,),
            ).fetchone()
            if not row:
                raise KeyError(action_id)
            if row["state"] != "dispatching":
                raise RuntimeError(
                    f"cannot mark uncertain from dispatch state={row['state']}"
                )
            now = utcnow()
            conn.execute(
                """UPDATE action_dispatches
                   SET state='uncertain',finished_at=?,error=?
                   WHERE action_id=?""",
                (now, error, action_id),
            )
            conn.execute(
                "UPDATE action_requests SET status='uncertain',updated_at=? WHERE id=?",
                (now, action_id),
            )
            conn.execute(
                "UPDATE action_warrant_consumptions "
                "SET disposition='uncertain' WHERE action_id=?",
                (action_id,),
            )
            conn.execute(
                "UPDATE tasks SET status='blocked',updated_at=? WHERE id=?",
                (now, row["task_id"]),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def record_external_dispatch_result(
        self,
        *,
        action_id: str,
        result,
        action_status: str,
    ) -> str:
        """Atomically persist ActionResult + dispatch outcome + action status."""
        result_id = uuid.uuid4().hex[:12]
        conn = self._connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT task_id,state,adapter FROM action_dispatches WHERE action_id=?",
                (action_id,),
            ).fetchone()
            if not row:
                raise KeyError(action_id)
            if row["state"] != "dispatching":
                raise RuntimeError(
                    f"result cannot be recorded from dispatch state={row['state']}"
                )
            if result.action_id != action_id:
                raise ValueError("result action_id mismatch")
            if result.adapter != row["adapter"]:
                raise ValueError("result adapter does not match durable dispatch adapter")

            final_dispatch_state = (
                "completed" if action_status == "completed" else "failed"
            )
            now = utcnow()
            evidence_json = json.dumps(
                [asdict(item) for item in result.evidence], ensure_ascii=False
            )
            conn.execute(
                """INSERT INTO action_results
                (id,action_id,created_at,status,evidence_json,external_id,error,adapter)
                VALUES(?,?,?,?,?,?,?,?)""",
                (
                    result_id,
                    action_id,
                    now,
                    result.status,
                    evidence_json,
                    result.external_id,
                    result.error,
                    result.adapter,
                ),
            )
            conn.execute(
                """UPDATE action_dispatches
                   SET state=?,finished_at=?,result_status=?,external_id=?,
                       error=?,result_evidence_json=?
                   WHERE action_id=?""",
                (
                    final_dispatch_state,
                    now,
                    result.status,
                    result.external_id,
                    result.error,
                    evidence_json,
                    action_id,
                ),
            )
            conn.execute(
                "UPDATE action_requests SET status=?,updated_at=? WHERE id=?",
                (action_status, now, action_id),
            )
            conn.execute(
                "UPDATE action_warrant_consumptions SET disposition=? WHERE action_id=?",
                (final_dispatch_state, action_id),
            )
            conn.commit()
            return result_id
        except Exception:
            conn.rollback()
            raise

    def reconcile_external_dispatch(
        self,
        *,
        action_id: str,
        effect_occurred: bool,
        reconciled_by: str,
        note: str = "",
        evidence: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Resolve an uncertain dispatch without resurrecting the consumed warrant."""
        from .dispatch import reconciliation_state

        if not reconciled_by or not str(reconciled_by).strip():
            raise ValueError("reconciled_by is required")
        conn = self._connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT task_id,state FROM action_dispatches WHERE action_id=?",
                (action_id,),
            ).fetchone()
            if not row:
                raise KeyError(action_id)
            if row["state"] != "uncertain":
                raise RuntimeError(
                    f"only uncertain dispatch can be reconciled; got {row['state']}"
                )

            state = reconciliation_state(effect_occurred=effect_occurred).value
            now = utcnow()
            evidence_json = json.dumps(evidence or [], ensure_ascii=False)
            conn.execute(
                """UPDATE action_dispatches
                   SET state=?,reconciled_at=?,reconciled_by=?,
                       reconciliation_note=?,reconciliation_evidence_json=?
                   WHERE action_id=?""",
                (
                    state,
                    now,
                    reconciled_by,
                    note,
                    evidence_json,
                    action_id,
                ),
            )
            conn.execute(
                "UPDATE action_requests SET status=?,updated_at=? WHERE id=?",
                (state, now, action_id),
            )
            conn.execute(
                "UPDATE action_warrant_consumptions SET disposition=? WHERE action_id=?",
                (state, action_id),
            )
            conn.execute(
                "UPDATE tasks SET status='blocked',updated_at=? WHERE id=?",
                (now, row["task_id"]),
            )
            conn.commit()
            return self.get_action_dispatch(action_id)
        except Exception:
            conn.rollback()
            raise

    def list_unresolved_dispatches(self) -> list[dict[str, Any]]:
        rows = self._connection().execute(
            """SELECT * FROM action_dispatches
               WHERE state IN ('dispatching','uncertain')
               ORDER BY started_at,action_id"""
        ).fetchall()
        return [dict(row) for row in rows]


    # ---- Temporal lifecycle / release / re-entry (Patch 004) ----

    def authorize_actions_atomically(
        self,
        *,
        task_id: str,
        approval_id: str,
        approval_note: str,
        bindings: list[tuple[str, object]],
    ) -> str:
        """Create approval + warrants + exact action bindings in one transaction.

        bindings: [(action_id, Warrant), ...]

        This removes the crash window where an action could be marked
        ready_for_action before its Warrant existed.
        """
        if not bindings:
            raise ValueError("no action bindings to authorize")
        conn = self._connection()
        try:
            conn.execute("BEGIN IMMEDIATE")

            task = conn.execute(
                "SELECT id,status FROM tasks WHERE id=?", (task_id,)
            ).fetchone()
            if not task:
                raise KeyError(task_id)
            if task["status"] != "waiting_approval":
                raise RuntimeError("task is not waiting for approval")

            conn.execute(
                "INSERT INTO approvals(id,task_id,created_at,decision,note) VALUES(?,?,?,?,?)",
                (approval_id, task_id, utcnow(), "approved", approval_note),
            )

            now = utcnow()
            for action_id, warrant in bindings:
                action = conn.execute(
                    """SELECT id,task_id,status,artifact_refs_json
                       FROM action_requests WHERE id=?""",
                    (action_id,),
                ).fetchone()
                if not action:
                    raise KeyError(action_id)
                if action["task_id"] != task_id:
                    raise RuntimeError("action belongs to different task")
                if action["status"] != "waiting_approval":
                    raise RuntimeError(
                        f"action {action_id} is not waiting for approval"
                    )

                raw = warrant.to_dict()
                conn.execute(
                    """INSERT INTO temporal_warrants
                    (warrant_id,domain,action_class,subject,target,claim_ids_json,
                     evidence_ids_json,issuer,policy_basis,issued_at,valid_from,
                     valid_to,status,scope_json,completion_condition,
                     provenance_json,created_at,updated_at,superseded_by,
                     revoked_reason,completed_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        raw["warrant_id"], raw["domain"], raw["action_class"],
                        raw["subject"], raw.get("target", ""),
                        json.dumps(raw.get("claim_ids") or [], ensure_ascii=False),
                        json.dumps(raw.get("evidence_ids") or [], ensure_ascii=False),
                        raw.get("issuer", ""), raw.get("policy_basis", ""),
                        raw["issued_at"], raw["valid_from"], raw.get("valid_to"),
                        raw["status"],
                        json.dumps(raw.get("scope") or {}, ensure_ascii=False),
                        raw.get("completion_condition", ""),
                        json.dumps(raw.get("provenance") or {}, ensure_ascii=False),
                        raw["created_at"], raw["updated_at"],
                        raw.get("superseded_by"),
                        raw.get("revoked_reason", ""),
                        raw.get("completed_at"),
                    ),
                )

                artifact_hashes = [
                    item.get("sha256")
                    for item in json.loads(action["artifact_refs_json"])
                ]
                conn.execute(
                    """INSERT INTO action_approvals
                    (action_id,approval_id,bound_at,artifact_hashes_json)
                    VALUES(?,?,?,?)""",
                    (
                        action_id,
                        approval_id,
                        now,
                        json.dumps(artifact_hashes, ensure_ascii=False),
                    ),
                )

                conn.execute(
                    """UPDATE action_requests
                       SET approval_id=?,warrant_id=?,warrant_bound_at=?,
                           status='ready_for_action',updated_at=?
                       WHERE id=?""",
                    (
                        approval_id,
                        raw["warrant_id"],
                        now,
                        now,
                        action_id,
                    ),
                )

            conn.execute(
                "UPDATE tasks SET status='ready_for_action',approval_reason='',updated_at=? "
                "WHERE id=?",
                (now, task_id),
            )
            conn.commit()
            return approval_id
        except Exception:
            conn.rollback()
            raise

    def persist_temporal_release(self, release, *, action_id: str) -> str:
        raw = release.to_dict() if hasattr(release, "to_dict") else dict(release)
        conn = self._connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            action = conn.execute(
                "SELECT warrant_id FROM action_requests WHERE id=?", (action_id,)
            ).fetchone()
            if not action:
                raise KeyError(action_id)
            if action["warrant_id"] != raw.get("prior_warrant_id"):
                raise RuntimeError("release/action warrant mismatch")

            conn.execute(
                """INSERT INTO temporal_releases
                (release_id,subject,prior_warrant_id,prior_claim_ids_json,
                 released_authority,reason,released_at,retains_historical_record,
                 restores_access,erases_consequences,provenance_json)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    raw["release_id"],
                    raw["subject"],
                    raw.get("prior_warrant_id"),
                    json.dumps(raw.get("prior_claim_ids") or [], ensure_ascii=False),
                    raw.get("released_authority", ""),
                    raw.get("reason", ""),
                    raw["released_at"],
                    1 if raw.get("retains_historical_record", True) else 0,
                    1 if raw.get("restores_access", False) else 0,
                    1 if raw.get("erases_consequences", False) else 0,
                    json.dumps(raw.get("provenance") or {}, ensure_ascii=False),
                ),
            )
            conn.execute(
                "UPDATE action_requests SET release_id=?,updated_at=? WHERE id=?",
                (raw["release_id"], utcnow(), action_id),
            )
            conn.commit()
            return str(raw["release_id"])
        except Exception:
            conn.rollback()
            raise

    def persist_temporal_evidence_event(self, event) -> str:
        raw = event.to_dict() if hasattr(event, "to_dict") else dict(event)
        conn = self._connection()
        conn.execute(
            """INSERT INTO temporal_evidence
            (evidence_id,kind,subject,content_json,source,observed_at,recorded_at,
             related_claim_ids_json,related_warrant_ids_json,sha256,confidence,
             tags_json,provenance_json)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                raw["evidence_id"], raw["kind"], raw["subject"],
                json.dumps(raw.get("content"), ensure_ascii=False, sort_keys=True),
                raw.get("source", ""), raw["observed_at"], raw["recorded_at"],
                json.dumps(raw.get("related_claim_ids") or [], ensure_ascii=False),
                json.dumps(raw.get("related_warrant_ids") or [], ensure_ascii=False),
                raw.get("sha256", ""), raw.get("confidence"),
                json.dumps(raw.get("tags") or [], ensure_ascii=False),
                json.dumps(raw.get("provenance") or {}, ensure_ascii=False),
            ),
        )
        conn.commit()
        return str(raw["evidence_id"])

    def persist_reevaluation_trigger(
        self,
        trigger,
        *,
        prior_action_id: str,
    ) -> str:
        raw = trigger.to_dict() if hasattr(trigger, "to_dict") else dict(trigger)
        conn = self._connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            action = conn.execute(
                "SELECT warrant_id FROM action_requests WHERE id=?",
                (prior_action_id,),
            ).fetchone()
            if not action:
                raise KeyError(prior_action_id)
            if action["warrant_id"] != raw.get("prior_warrant_id"):
                raise RuntimeError("reevaluation/action warrant mismatch")

            conn.execute(
                """INSERT INTO temporal_reevaluation_triggers
                (trigger_id,prior_disposition,prior_task_id,prior_warrant_id,
                 prior_claim_ids_json,new_evidence_ids_json,reason,created_at,
                 new_evaluation_id,provenance_json)
                VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    raw["trigger_id"], raw["prior_disposition"],
                    raw.get("prior_task_id"), raw.get("prior_warrant_id"),
                    json.dumps(raw.get("prior_claim_ids") or [], ensure_ascii=False),
                    json.dumps(raw.get("new_evidence_ids") or [], ensure_ascii=False),
                    raw.get("reason", ""), raw["created_at"],
                    raw.get("new_evaluation_id"),
                    json.dumps(raw.get("provenance") or {}, ensure_ascii=False),
                ),
            )
            conn.execute(
                "UPDATE action_requests SET reevaluation_trigger_id=?,updated_at=? "
                "WHERE id=?",
                (raw["trigger_id"], utcnow(), prior_action_id),
            )
            conn.commit()
            return str(raw["trigger_id"])
        except Exception:
            conn.rollback()
            raise

    def get_temporal_release_for_action(self, action_id: str) -> dict[str, Any] | None:
        row = self._connection().execute(
            """SELECT r.*
               FROM temporal_releases r
               JOIN action_requests a ON a.release_id=r.release_id
               WHERE a.id=?""",
            (action_id,),
        ).fetchone()
        return dict(row) if row else None

    def set_task_budget(self, task_id: str, limits) -> None:
        raw = limits.to_dict() if hasattr(limits, "to_dict") else dict(limits or {})
        conn = self._connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """INSERT INTO task_budgets
                (task_id,max_model_calls,max_tool_calls,max_total_tokens,max_elapsed_seconds,max_cost_usd,created_at)
                VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(task_id) DO UPDATE SET
                  max_model_calls=excluded.max_model_calls,
                  max_tool_calls=excluded.max_tool_calls,
                  max_total_tokens=excluded.max_total_tokens,
                  max_elapsed_seconds=excluded.max_elapsed_seconds,
                  max_cost_usd=excluded.max_cost_usd""",
                (
                    task_id,
                    raw.get("max_model_calls"),
                    raw.get("max_tool_calls"),
                    raw.get("max_total_tokens"),
                    raw.get("max_elapsed_seconds"),
                    raw.get("max_cost_usd"),
                    utcnow(),
                ),
            )
            conn.execute(
                """INSERT OR IGNORE INTO task_usage(
                   task_id,model_calls,tool_calls,total_tokens,cost_usd,updated_at,
                   tool_offers,tool_invocations,tool_invocation_unknown_calls,cost_unknown_calls
                   ) VALUES(?,0,0,0,0,?,0,0,0,0)""",
                (task_id, utcnow()),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def get_task_budget(self, task_id: str) -> dict[str, Any] | None:
        row = self._connection().execute(
            "SELECT * FROM task_budgets WHERE task_id=?", (task_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_task_usage(self, task_id: str) -> dict[str, Any]:
        row = self._connection().execute(
            "SELECT * FROM task_usage WHERE task_id=?", (task_id,)
        ).fetchone()
        if row:
            return dict(row)
        return {
            "task_id": task_id,
            "model_calls": 0,
            "tool_calls": 0,
            "tool_offers": 0,
            "tool_invocations": 0,
            "tool_invocation_unknown_calls": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
            "cost_unknown_calls": 0,
            "updated_at": None,
        }

    def add_task_usage(
        self,
        task_id: str,
        *,
        model_calls: int = 0,
        tool_offers: int = 0,
        tool_invocations: int = 0,
        tool_invocation_unknown_calls: int = 0,
        total_tokens: int = 0,
        cost_usd: float = 0.0,
        cost_unknown_calls: int = 0,
        tool_calls: int | None = None,
    ) -> dict[str, Any]:
        # Backward compatibility: pre-schema-22 callers used tool_calls to mean
        # len(tools), which is an offer count. Preserve that meaning only.
        if tool_calls is not None:
            if tool_offers and int(tool_offers) != int(tool_calls):
                raise ValueError("tool_calls legacy alias conflicts with tool_offers")
            tool_offers = int(tool_calls)

        conn = self._connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """INSERT OR IGNORE INTO task_usage(
                   task_id,model_calls,tool_calls,total_tokens,cost_usd,updated_at,
                   tool_offers,tool_invocations,tool_invocation_unknown_calls,cost_unknown_calls
                   ) VALUES(?,0,0,0,0,?,0,0,0,0)""",
                (task_id, utcnow()),
            )
            conn.execute(
                """UPDATE task_usage SET
                model_calls=model_calls+?,
                tool_calls=tool_calls+?,
                tool_offers=tool_offers+?,
                tool_invocations=tool_invocations+?,
                tool_invocation_unknown_calls=tool_invocation_unknown_calls+?,
                total_tokens=total_tokens+?,
                cost_usd=cost_usd+?,
                cost_unknown_calls=cost_unknown_calls+?,
                updated_at=?
                WHERE task_id=?""",
                (
                    int(model_calls),
                    int(tool_offers),
                    int(tool_offers),
                    int(tool_invocations),
                    int(tool_invocation_unknown_calls),
                    int(total_tokens),
                    float(cost_usd),
                    int(cost_unknown_calls),
                    utcnow(),
                    task_id,
                ),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        return self.get_task_usage(task_id)

    # -------------------------------------------------------------------------
    # Temporal authority / continuing evidence layer
    # -------------------------------------------------------------------------

    def add_temporal_claim(self, claim) -> str:
        """Persist a durable claim. Claims are information only; never authority."""
        from stillpoint.temporal.claims import Claim
        if not isinstance(claim, Claim):
            raise TypeError("expected Claim")
        conn = self._connection()
        d = claim.to_dict()
        conn.execute(
            """INSERT INTO temporal_claims
            (claim_id,subject,predicate,value_json,domain,source,evidence_refs_json,
             time_observed,time_asserted,effective_from,effective_to,confidence,status,
             supersedes,superseded_by,review_conditions_json,provenance_json,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                d["claim_id"],
                d["subject"],
                d["predicate"],
                json.dumps(d.get("value"), ensure_ascii=False),
                d["domain"],
                d["source"],
                json.dumps(d.get("evidence_refs") or [], ensure_ascii=False),
                d.get("time_observed") or "",
                d["time_asserted"],
                d.get("effective_from"),
                d.get("effective_to"),
                d.get("confidence"),
                d["status"],
                d.get("supersedes"),
                d.get("superseded_by"),
                json.dumps(d.get("review_conditions") or [], ensure_ascii=False),
                json.dumps(d.get("provenance") or {}, ensure_ascii=False),
                d["created_at"],
                d["updated_at"],
            ),
        )
        conn.commit()
        return d["claim_id"]

    def update_temporal_claim(self, claim) -> None:
        from stillpoint.temporal.claims import Claim
        if not isinstance(claim, Claim):
            raise TypeError("expected Claim")
        d = claim.to_dict()
        conn = self._connection()
        conn.execute(
            """UPDATE temporal_claims SET
            value_json=?, status=?, superseded_by=?, review_conditions_json=?,
            provenance_json=?, updated_at=?, confidence=?, effective_to=?
            WHERE claim_id=?""",
            (
                json.dumps(d.get("value"), ensure_ascii=False),
                d["status"],
                d.get("superseded_by"),
                json.dumps(d.get("review_conditions") or [], ensure_ascii=False),
                json.dumps(d.get("provenance") or {}, ensure_ascii=False),
                d["updated_at"],
                d.get("confidence"),
                d.get("effective_to"),
                d["claim_id"],
            ),
        )
        conn.commit()

    def get_temporal_claim(self, claim_id: str):
        from stillpoint.temporal.claims import Claim
        row = self._connection().execute(
            "SELECT * FROM temporal_claims WHERE claim_id=?", (claim_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_claim(dict(row))

    def list_temporal_claims(self, subject: str | None = None, domain: str | None = None, status: str | None = None):
        conn = self._connection()
        clauses = []
        params: list[Any] = []
        if subject:
            clauses.append("subject=?")
            params.append(subject)
        if domain:
            clauses.append("domain=?")
            params.append(domain)
        if status:
            clauses.append("status=?")
            params.append(status)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM temporal_claims{where} ORDER BY time_asserted, claim_id", params
        ).fetchall()
        return [self._row_to_claim(dict(r)) for r in rows]

    def _row_to_claim(self, row: dict[str, Any]):
        from stillpoint.temporal.claims import Claim
        raw = {
            "claim_id": row["claim_id"],
            "subject": row["subject"],
            "predicate": row["predicate"],
            "value": json.loads(row["value_json"]) if row["value_json"] is not None else None,
            "domain": row["domain"],
            "source": row["source"],
            "evidence_refs": json.loads(row["evidence_refs_json"] or "[]"),
            "time_observed": row["time_observed"] or "",
            "time_asserted": row["time_asserted"],
            "effective_from": row["effective_from"],
            "effective_to": row["effective_to"],
            "confidence": row["confidence"],
            "status": row["status"],
            "supersedes": row["supersedes"],
            "superseded_by": row["superseded_by"],
            "review_conditions": json.loads(row["review_conditions_json"] or "[]"),
            "provenance": json.loads(row["provenance_json"] or "{}"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        return Claim.from_dict(raw)

    def add_temporal_warrant(self, warrant) -> str:
        from stillpoint.temporal.warrants import Warrant
        if not isinstance(warrant, Warrant):
            raise TypeError("expected Warrant")
        d = warrant.to_dict()
        conn = self._connection()
        conn.execute(
            """INSERT INTO temporal_warrants
            (warrant_id,domain,action_class,subject,target,claim_ids_json,evidence_ids_json,
             issuer,policy_basis,issued_at,valid_from,valid_to,status,scope_json,
             completion_condition,provenance_json,created_at,updated_at,superseded_by,
             revoked_reason,completed_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                d["warrant_id"],
                d["domain"],
                d["action_class"],
                d["subject"],
                d.get("target") or "",
                json.dumps(d.get("claim_ids") or [], ensure_ascii=False),
                json.dumps(d.get("evidence_ids") or [], ensure_ascii=False),
                d.get("issuer") or "",
                d.get("policy_basis") or "",
                d["issued_at"],
                d["valid_from"],
                d.get("valid_to"),
                d["status"],
                json.dumps(d.get("scope") or {}, ensure_ascii=False),
                d.get("completion_condition") or "",
                json.dumps(d.get("provenance") or {}, ensure_ascii=False),
                d["created_at"],
                d["updated_at"],
                d.get("superseded_by"),
                d.get("revoked_reason") or "",
                d.get("completed_at"),
            ),
        )
        conn.commit()
        return d["warrant_id"]

    def update_temporal_warrant(self, warrant) -> None:
        from stillpoint.temporal.warrants import Warrant
        if not isinstance(warrant, Warrant):
            raise TypeError("expected Warrant")
        d = warrant.to_dict()
        conn = self._connection()
        conn.execute(
            """UPDATE temporal_warrants SET
            status=?, valid_to=?, superseded_by=?, revoked_reason=?, completed_at=?,
            provenance_json=?, updated_at=?
            WHERE warrant_id=?""",
            (
                d["status"],
                d.get("valid_to"),
                d.get("superseded_by"),
                d.get("revoked_reason") or "",
                d.get("completed_at"),
                json.dumps(d.get("provenance") or {}, ensure_ascii=False),
                d["updated_at"],
                d["warrant_id"],
            ),
        )
        conn.commit()

    def get_temporal_warrant(self, warrant_id: str):
        row = self._connection().execute(
            "SELECT * FROM temporal_warrants WHERE warrant_id=?", (warrant_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_warrant(dict(row))

    def list_temporal_warrants(self, subject: str | None = None, domain: str | None = None, status: str | None = None):
        conn = self._connection()
        clauses = []
        params: list[Any] = []
        if subject:
            clauses.append("subject=?")
            params.append(subject)
        if domain:
            clauses.append("domain=?")
            params.append(domain)
        if status:
            clauses.append("status=?")
            params.append(status)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM temporal_warrants{where} ORDER BY issued_at, warrant_id", params
        ).fetchall()
        return [self._row_to_warrant(dict(r)) for r in rows]

    def _row_to_warrant(self, row: dict[str, Any]):
        from stillpoint.temporal.warrants import Warrant
        raw = {
            "warrant_id": row["warrant_id"],
            "domain": row["domain"],
            "action_class": row["action_class"],
            "subject": row["subject"],
            "target": row["target"] or "",
            "claim_ids": json.loads(row["claim_ids_json"] or "[]"),
            "evidence_ids": json.loads(row["evidence_ids_json"] or "[]"),
            "issuer": row["issuer"] or "",
            "policy_basis": row["policy_basis"] or "",
            "issued_at": row["issued_at"],
            "valid_from": row["valid_from"],
            "valid_to": row["valid_to"],
            "status": row["status"],
            "scope": json.loads(row["scope_json"] or "{}"),
            "completion_condition": row["completion_condition"] or "",
            "provenance": json.loads(row["provenance_json"] or "{}"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "superseded_by": row["superseded_by"],
            "revoked_reason": row["revoked_reason"] or "",
            "completed_at": row["completed_at"],
        }
        return Warrant.from_dict(raw)

    def add_temporal_evidence(self, evidence) -> str:
        from stillpoint.temporal.evidence import EvidenceEvent
        if not isinstance(evidence, EvidenceEvent):
            raise TypeError("expected EvidenceEvent")
        d = evidence.to_dict()
        conn = self._connection()
        conn.execute(
            """INSERT INTO temporal_evidence
            (evidence_id,kind,subject,content_json,source,observed_at,recorded_at,
             related_claim_ids_json,related_warrant_ids_json,sha256,confidence,tags_json,provenance_json)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                d["evidence_id"],
                d["kind"],
                d["subject"],
                json.dumps(d.get("content"), ensure_ascii=False),
                d["source"],
                d["observed_at"],
                d["recorded_at"],
                json.dumps(d.get("related_claim_ids") or [], ensure_ascii=False),
                json.dumps(d.get("related_warrant_ids") or [], ensure_ascii=False),
                d.get("sha256") or "",
                d.get("confidence"),
                json.dumps(d.get("tags") or [], ensure_ascii=False),
                json.dumps(d.get("provenance") or {}, ensure_ascii=False),
            ),
        )
        conn.commit()
        return d["evidence_id"]

    def get_temporal_evidence(self, evidence_id: str):
        row = self._connection().execute(
            "SELECT * FROM temporal_evidence WHERE evidence_id=?", (evidence_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_evidence(dict(row))

    def list_temporal_evidence(self, subject: str | None = None):
        conn = self._connection()
        if subject:
            rows = conn.execute(
                "SELECT * FROM temporal_evidence WHERE subject=? ORDER BY recorded_at, evidence_id",
                (subject,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM temporal_evidence ORDER BY recorded_at, evidence_id"
            ).fetchall()
        return [self._row_to_evidence(dict(r)) for r in rows]

    def _row_to_evidence(self, row: dict[str, Any]):
        from stillpoint.temporal.evidence import EvidenceEvent
        raw = {
            "evidence_id": row["evidence_id"],
            "kind": row["kind"],
            "subject": row["subject"],
            "content": json.loads(row["content_json"]) if row["content_json"] is not None else None,
            "source": row["source"],
            "observed_at": row["observed_at"],
            "recorded_at": row["recorded_at"],
            "related_claim_ids": json.loads(row["related_claim_ids_json"] or "[]"),
            "related_warrant_ids": json.loads(row["related_warrant_ids_json"] or "[]"),
            "sha256": row["sha256"] or "",
            "confidence": row["confidence"],
            "tags": json.loads(row["tags_json"] or "[]"),
            "provenance": json.loads(row["provenance_json"] or "{}"),
        }
        return EvidenceEvent.from_dict(raw)

    def add_reevaluation_trigger(self, trigger) -> str:
        from stillpoint.temporal.reentry import ReevaluationTrigger
        if not isinstance(trigger, ReevaluationTrigger):
            raise TypeError("expected ReevaluationTrigger")
        d = trigger.to_dict()
        conn = self._connection()
        conn.execute(
            """INSERT INTO temporal_reevaluation_triggers
            (trigger_id,prior_disposition,prior_task_id,prior_warrant_id,prior_claim_ids_json,
             new_evidence_ids_json,reason,created_at,new_evaluation_id,provenance_json)
            VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                d["trigger_id"],
                d["prior_disposition"],
                d.get("prior_task_id"),
                d.get("prior_warrant_id"),
                json.dumps(d.get("prior_claim_ids") or [], ensure_ascii=False),
                json.dumps(d.get("new_evidence_ids") or [], ensure_ascii=False),
                d.get("reason") or "",
                d["created_at"],
                d.get("new_evaluation_id"),
                json.dumps(d.get("provenance") or {}, ensure_ascii=False),
            ),
        )
        conn.commit()
        return d["trigger_id"]

    def add_temporal_release(self, release) -> str:
        from stillpoint.temporal.reentry import ReleaseRecord
        if not isinstance(release, ReleaseRecord):
            raise TypeError("expected ReleaseRecord")
        d = release.to_dict()
        conn = self._connection()
        conn.execute(
            """INSERT INTO temporal_releases
            (release_id,subject,prior_warrant_id,prior_claim_ids_json,released_authority,
             reason,released_at,retains_historical_record,restores_access,erases_consequences,provenance_json)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (
                d["release_id"],
                d["subject"],
                d.get("prior_warrant_id"),
                json.dumps(d.get("prior_claim_ids") or [], ensure_ascii=False),
                d.get("released_authority") or "",
                d.get("reason") or "",
                d["released_at"],
                1 if d.get("retains_historical_record", True) else 0,
                1 if d.get("restores_access", False) else 0,
                1 if d.get("erases_consequences", False) else 0,
                json.dumps(d.get("provenance") or {}, ensure_ascii=False),
            ),
        )
        conn.commit()
        return d["release_id"]
