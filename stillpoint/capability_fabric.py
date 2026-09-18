from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .capabilities import ToolRequest


class CapabilityConfigurationError(RuntimeError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _now()).astimezone(timezone.utc).isoformat()


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)


def capability_manifest_path(root: Path) -> Path:
    root = Path(root).resolve()
    local = root / "config" / "capabilities.json"
    if local.is_file():
        return local
    return Path(__file__).resolve().parent / "defaults" / "capabilities.json"


class CapabilityBroker:
    """Durable capability custody for StillPoint offices.

    This broker governs whether a model call may be offered a non-external
    provider capability. It does not issue ActionRequests, temporal warrants, or
    external dispatch rights.

    Manifest synchronization is intentionally non-revivifying: missing grants are
    seeded, but an existing suspended/revoked grant is never reset to active merely
    because the packaged manifest still contains it.
    """

    def __init__(self, db, manifest_path: Path):
        self.db = db
        self.manifest_path = Path(manifest_path)
        raw = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        if int(raw.get("version", 0)) != 1:
            raise CapabilityConfigurationError("unsupported capability manifest version")
        self.raw = raw
        self.definitions = {}
        for item in raw.get("capabilities") or []:
            cid = str(item.get("id") or "").strip()
            if not cid or cid in self.definitions:
                raise CapabilityConfigurationError("duplicate/empty capability id")
            kind = str(item.get("kind") or "")
            external = bool(item.get("external_effect", False))
            if kind in {"provider_tool", "provider_control"} and external:
                raise CapabilityConfigurationError(
                    f"provider capability {cid} may not carry external_effect=true"
                )
            self.definitions[cid] = {
                "capability_id": cid,
                "kind": kind,
                "external_effect": external,
                "description": str(item.get("description") or "").strip(),
                "metadata": dict(item.get("metadata") or {}),
            }

        self.grant_specs = []
        seen = set()
        for grant in raw.get("grants") or []:
            role = str(grant.get("role") or "").strip()
            granted_by = str(grant.get("granted_by") or "").strip()
            for cid in grant.get("capabilities") or []:
                cid = str(cid)
                key = (role, cid)
                if key in seen:
                    raise CapabilityConfigurationError(f"duplicate capability grant {role}:{cid}")
                seen.add(key)
                if cid not in self.definitions:
                    raise CapabilityConfigurationError(f"grant references unknown capability {cid}")
                if self.definitions[cid]["external_effect"]:
                    raise CapabilityConfigurationError(
                        f"Stage 3 manifest may not grant external-effect capability {cid}"
                    )
                self.grant_specs.append({
                    "role": role,
                    "capability_id": cid,
                    "granted_by": granted_by,
                    "constraints": dict(grant.get("constraints") or {}),
                })

    def sync_manifest(self, *, now_iso: str | None = None) -> dict[str, int]:
        now_iso = now_iso or _iso()
        conn = self.db._connection()
        inserted_capabilities = 0
        inserted_grants = 0
        suspended_grants = 0
        canonical_grants = {
            (grant["role"], grant["capability_id"])
            for grant in self.grant_specs
        }

        try:
            conn.execute("BEGIN IMMEDIATE")

            for definition in self.definitions.values():
                row = conn.execute(
                    "SELECT kind,external_effect,status FROM company_capabilities WHERE capability_id=?",
                    (definition["capability_id"],),
                ).fetchone()
                if row:
                    if row["kind"] != definition["kind"] or int(row["external_effect"]) != int(definition["external_effect"]):
                        raise CapabilityConfigurationError(
                            f"durable capability definition drift: {definition['capability_id']}"
                        )
                    continue
                conn.execute(
                    """INSERT INTO company_capabilities(
                       capability_id,kind,external_effect,description,status,metadata_json,created_at,updated_at
                       ) VALUES(?,?,?,?,?,?,?,?)""",
                    (
                        definition["capability_id"],
                        definition["kind"],
                        1 if definition["external_effect"] else 0,
                        definition["description"],
                        "active",
                        json.dumps(definition["metadata"], sort_keys=True),
                        now_iso,
                        now_iso,
                    ),
                )
                inserted_capabilities += 1

            for grant in self.grant_specs:
                row = conn.execute(
                    "SELECT status FROM office_capability_grants WHERE role=? AND capability_id=?",
                    (grant["role"], grant["capability_id"]),
                ).fetchone()
                if row:
                    continue
                conn.execute(
                    """INSERT INTO office_capability_grants(
                       role,capability_id,status,granted_by,valid_from,review_by,constraints_json,created_at,updated_at
                       ) VALUES(?,?,?,?,?,?,?,?,?)""",
                    (
                        grant["role"],
                        grant["capability_id"],
                        "active",
                        grant["granted_by"],
                        now_iso,
                        None,
                        json.dumps(grant["constraints"], sort_keys=True),
                        now_iso,
                        now_iso,
                    ),
                )
                inserted_grants += 1

            durable_grants = conn.execute(
                """SELECT role,capability_id,status
                   FROM office_capability_grants"""
            ).fetchall()
            for row in durable_grants:
                key = (row["role"], row["capability_id"])
                if row["status"] != "active" or key in canonical_grants:
                    continue
                conn.execute(
                    """UPDATE office_capability_grants
                       SET status='suspended',updated_at=?
                       WHERE role=? AND capability_id=?""",
                    (now_iso, row["role"], row["capability_id"]),
                )
                self._event(
                    role=row["role"],
                    capability_id=row["capability_id"],
                    event_type="grant_changed",
                    detail={
                        "from_status": "active",
                        "to_status": "suspended",
                        "changed_by": "manifest_reconciliation",
                        "reason": "grant_not_present_in_current_manifest",
                        "external_authority_granted": False,
                    },
                    now_iso=now_iso,
                    conn=conn,
                    commit=False,
                )
                suspended_grants += 1

            conn.commit()
        except Exception:
            conn.rollback()
            raise

        return {
            "inserted_capabilities": inserted_capabilities,
            "inserted_grants": inserted_grants,
            "suspended_grants": suspended_grants,
        }

    def _event(
        self,
        *,
        role: str,
        capability_id: str,
        event_type: str,
        task_id: str | None = None,
        phase: str = "",
        provider: str = "",
        detail: dict[str, Any] | None = None,
        now_iso: str | None = None,
        conn=None,
        commit: bool = True,
    ) -> str:
        event_id = uuid.uuid4().hex
        conn = conn or self.db._connection()
        conn.execute(
            """INSERT INTO capability_events(
               event_id,task_id,role,phase,capability_id,event_type,provider,occurred_at,detail_json
               ) VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                event_id,
                task_id,
                role,
                phase or "",
                capability_id,
                event_type,
                provider or "",
                now_iso or _iso(),
                json.dumps(detail or {}, sort_keys=True),
            ),
        )
        if commit:
            conn.commit()
        return event_id

    def _grant_current(self, row, *, now: datetime) -> bool:
        if not row or row["status"] != "active":
            return False
        valid_from = _parse(row["valid_from"])
        review_by = _parse(row["review_by"])
        if valid_from and now < valid_from:
            return False
        if review_by and now >= review_by:
            return False
        return True

    def is_granted(self, role: str, capability_id: str, *, now_iso: str | None = None) -> bool:
        now = _parse(now_iso) if now_iso else _now()
        conn = self.db._connection()
        cap = conn.execute(
            "SELECT status,kind,external_effect FROM company_capabilities WHERE capability_id=?",
            (capability_id,),
        ).fetchone()
        if not cap or cap["status"] != "active" or int(cap["external_effect"]) != 0:
            return False
        row = conn.execute(
            """SELECT status,valid_from,review_by
               FROM office_capability_grants WHERE role=? AND capability_id=?""",
            (role, capability_id),
        ).fetchone()
        return self._grant_current(row, now=now)

    def resolve_provider_requests(
        self,
        *,
        role: str,
        requests: Iterable[ToolRequest],
        declared_capabilities: Iterable[str],
        task_id: str | None,
        phase: str,
        provider: str = "",
    ) -> list[ToolRequest]:
        declared = set(declared_capabilities or [])
        output: list[ToolRequest] = []
        seen = set()
        conn = self.db._connection()
        for request in requests or []:
            cid = request.capability
            if cid in seen:
                continue
            seen.add(cid)
            definition = conn.execute(
                """SELECT kind,external_effect,status
                   FROM company_capabilities WHERE capability_id=?""",
                (cid,),
            ).fetchone()
            reason = ""
            if cid not in declared:
                reason = "capability_not_declared_by_current_work_plan"
            elif not definition:
                reason = "capability_not_registered"
            elif definition["status"] != "active":
                reason = "capability_not_active"
            elif definition["kind"] != "provider_tool":
                reason = "capability_is_not_provider_tool"
            elif int(definition["external_effect"]) != 0:
                reason = "external_effect_capability_cannot_enter_model_tool_envelope"
            elif not self.is_granted(role, cid):
                reason = "office_grant_not_current"

            if reason:
                if definition:
                    self._event(
                        role=role,
                        capability_id=cid,
                        event_type="blocked",
                        task_id=task_id,
                        phase=phase,
                        provider=provider,
                        detail={"reason": reason},
                    )
                continue

            self._event(
                role=role,
                capability_id=cid,
                event_type="offered",
                task_id=task_id,
                phase=phase,
                provider=provider,
                detail={
                    "meaning": "capability offered to provider model call",
                    "tool_use_proven": False,
                    "external_authority_granted": False,
                },
            )
            output.append(request)
        return output

    def set_grant_status(
        self,
        role: str,
        capability_id: str,
        status: str,
        *,
        changed_by: str,
        reason: str = "",
        now_iso: str | None = None,
    ) -> None:
        if status not in {"active", "suspended", "revoked"}:
            raise ValueError(status)
        if status == "active":
            canonical_grants = {
                (grant["role"], grant["capability_id"])
                for grant in self.grant_specs
            }
            if (role, capability_id) not in canonical_grants:
                raise CapabilityConfigurationError(
                    f"cannot activate grant absent from current manifest: {role}:{capability_id}"
                )

        now_iso = now_iso or _iso()
        conn = self.db._connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT status FROM office_capability_grants WHERE role=? AND capability_id=?",
                (role, capability_id),
            ).fetchone()
            if not row:
                raise KeyError((role, capability_id))
            conn.execute(
                """UPDATE office_capability_grants
                   SET status=?,updated_at=? WHERE role=? AND capability_id=?""",
                (status, now_iso, role, capability_id),
            )
            self._event(
                role=role,
                capability_id=capability_id,
                event_type="grant_changed",
                detail={
                    "from_status": row["status"],
                    "to_status": status,
                    "changed_by": changed_by,
                    "reason": reason,
                    "external_authority_granted": False,
                },
                now_iso=now_iso,
                conn=conn,
                commit=False,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def list_events(self, *, limit: int = 100) -> list[dict]:
        rows = self.db._connection().execute(
            """SELECT * FROM capability_events
               ORDER BY occurred_at DESC,event_id DESC LIMIT ?""",
            (int(limit),),
        ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            try:
                item["detail"] = json.loads(item.pop("detail_json") or "{}")
            except Exception:
                item["detail"] = {}
            out.append(item)
        return out

    def audit_manifest(self) -> dict[str, Any]:
        missing_capabilities = []
        definition_mismatches = []
        missing_grants = []
        unexpected_active_capabilities = []
        unexpected_active_grants = []
        conn = self.db._connection()
        for cid, definition in self.definitions.items():
            row = conn.execute(
                "SELECT kind,external_effect FROM company_capabilities WHERE capability_id=?",
                (cid,),
            ).fetchone()
            if not row:
                missing_capabilities.append(cid)
            elif row["kind"] != definition["kind"] or int(row["external_effect"]) != int(definition["external_effect"]):
                definition_mismatches.append(cid)
        for grant in self.grant_specs:
            row = conn.execute(
                "SELECT status FROM office_capability_grants WHERE role=? AND capability_id=?",
                (grant["role"], grant["capability_id"]),
            ).fetchone()
            if not row:
                missing_grants.append(f"{grant['role']}:{grant['capability_id']}")
        canonical_capabilities = set(self.definitions)
        canonical_grants = {
            (grant["role"], grant["capability_id"])
            for grant in self.grant_specs
        }
        for row in conn.execute(
            """SELECT capability_id FROM company_capabilities
               WHERE status='active' ORDER BY capability_id"""
        ).fetchall():
            if row["capability_id"] not in canonical_capabilities:
                unexpected_active_capabilities.append(row["capability_id"])
        for row in conn.execute(
            """SELECT role,capability_id FROM office_capability_grants
               WHERE status='active' ORDER BY role,capability_id"""
        ).fetchall():
            key = (row["role"], row["capability_id"])
            if key not in canonical_grants:
                unexpected_active_grants.append(f"{row['role']}:{row['capability_id']}")

        external_provider_caps = [
            cid for cid, definition in self.definitions.items()
            if definition["kind"] in {"provider_tool", "provider_control"} and definition["external_effect"]
        ]
        return {
            "ok": (
                not missing_capabilities
                and not definition_mismatches
                and not missing_grants
                and not unexpected_active_capabilities
                and not unexpected_active_grants
                and not external_provider_caps
            ),
            "manifest": str(self.manifest_path),
            "manifest_version": int(self.raw["version"]),
            "capability_count": len(self.definitions),
            "grant_count": len(self.grant_specs),
            "missing_capabilities": missing_capabilities,
            "definition_mismatches": definition_mismatches,
            "missing_grants": missing_grants,
            "unexpected_active_capabilities": unexpected_active_capabilities,
            "unexpected_active_grants": unexpected_active_grants,
            "external_effect_provider_capabilities": external_provider_caps,
            "manifest_reactivates_existing_grants": False,
            "manifest_suspends_removed_active_grants": True,
        }

    def snapshot(self, *, include_events: bool = True) -> dict[str, Any]:
        conn = self.db._connection()
        catalog = [dict(r) for r in conn.execute(
            """SELECT capability_id,kind,external_effect,description,status
               FROM company_capabilities ORDER BY capability_id"""
        ).fetchall()]
        grants = [dict(r) for r in conn.execute(
            """SELECT role,capability_id,status,granted_by,valid_from,review_by,constraints_json
               FROM office_capability_grants ORDER BY role,capability_id"""
        ).fetchall()]
        for row in grants:
            try:
                row["constraints"] = json.loads(row.pop("constraints_json") or "{}")
            except Exception:
                row["constraints"] = {}
        active_by_office: dict[str, list[str]] = {}
        for row in grants:
            if self.is_granted(row["role"], row["capability_id"]):
                active_by_office.setdefault(row["role"], []).append(row["capability_id"])
        out = {
            "kind": "company_capability_fabric",
            "authority_semantics": "capability grant != external-action authority",
            "catalog": catalog,
            "grants": grants,
            "active_by_office": active_by_office,
            "manifest_audit": self.audit_manifest(),
        }
        if include_events:
            out["recent_events"] = self.list_events(limit=50)
        return out
