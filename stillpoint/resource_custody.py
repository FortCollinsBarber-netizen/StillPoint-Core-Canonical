"""Durable quarantine and activation for dynamically acquired resources.

Possession is evidence, not authorization.

A resource may be discovered or acquired without becoming executable.  Its
capabilities are resolved under quarantine, then an already-issued temporal
warrant must explicitly activate only the portion that fits inside the
parent authority envelope.  One-shot resources are consumed at the durable
pre-effect boundary so crash/retry cannot resurrect authority.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any, Iterable

from .db import utcnow


class ResourceCustodyError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _caps(values: Iterable[str] | None) -> tuple[str, ...]:
    cleaned = {str(value).strip() for value in (values or ()) if str(value).strip()}
    return tuple(sorted(cleaned))


@dataclass(frozen=True)
class AcquiredResource:
    resource_id: str
    owner_role: str
    kind: str
    status: str
    discovered_capabilities: tuple[str, ...]
    resolved_capabilities: tuple[str, ...]
    authorized_capabilities: tuple[str, ...]
    parent_capabilities: tuple[str, ...]
    activation_warrant_id: str | None
    one_shot: bool
    acquired_at: str
    resolved_at: str | None
    activated_at: str | None
    consumed_at: str | None
    expired_at: str | None
    provenance: dict[str, Any]


class AcquiredResourceCustody:
    """Fail-closed custody boundary for dynamically acquired capability."""

    def __init__(self, db) -> None:
        self.db = db

    def _row(self, resource_id: str):
        return self.db._connection().execute(
            "SELECT * FROM acquired_resources WHERE resource_id=?",
            (resource_id,),
        ).fetchone()

    @staticmethod
    def _decode(row) -> AcquiredResource:
        if row is None:
            raise KeyError("acquired resource not found")
        raw = dict(row)
        return AcquiredResource(
            resource_id=raw["resource_id"],
            owner_role=raw["owner_role"],
            kind=raw["kind"],
            status=raw["status"],
            discovered_capabilities=tuple(json.loads(raw["discovered_capabilities_json"] or "[]")),
            resolved_capabilities=tuple(json.loads(raw["resolved_capabilities_json"] or "[]")),
            authorized_capabilities=tuple(json.loads(raw["authorized_capabilities_json"] or "[]")),
            parent_capabilities=tuple(json.loads(raw["parent_capabilities_json"] or "[]")),
            activation_warrant_id=raw["activation_warrant_id"],
            one_shot=bool(raw["one_shot"]),
            acquired_at=raw["acquired_at"],
            resolved_at=raw["resolved_at"],
            activated_at=raw["activated_at"],
            consumed_at=raw["consumed_at"],
            expired_at=raw["expired_at"],
            provenance=json.loads(raw["provenance_json"] or "{}"),
        )

    def get(self, resource_id: str) -> AcquiredResource:
        row = self._row(resource_id)
        if row is None:
            raise KeyError(resource_id)
        return self._decode(row)

    def _event(
        self,
        resource_id: str,
        event_type: str,
        *,
        detail: dict[str, Any] | None = None,
        now_iso: str | None = None,
        conn=None,
        commit: bool = True,
    ) -> str:
        conn = conn or self.db._connection()
        event_id = uuid.uuid4().hex
        conn.execute(
            """INSERT INTO acquired_resource_events(
               event_id,resource_id,event_type,occurred_at,detail_json
               ) VALUES(?,?,?,?,?)""",
            (
                event_id,
                resource_id,
                event_type,
                now_iso or utcnow(),
                json.dumps(detail or {}, sort_keys=True),
            ),
        )
        if commit:
            conn.commit()
        return event_id

    def acquire(
        self,
        *,
        resource_id: str,
        owner_role: str,
        kind: str,
        discovered_capabilities: Iterable[str] = (),
        one_shot: bool = False,
        provenance: dict[str, Any] | None = None,
        now_iso: str | None = None,
    ) -> AcquiredResource:
        resource_id = str(resource_id).strip()
        owner_role = str(owner_role).strip()
        kind = str(kind).strip()
        if not resource_id or not owner_role or not kind:
            raise ResourceCustodyError("INVALID_RESOURCE_IDENTITY", "resource id, owner role, and kind are required")
        discovered = _caps(discovered_capabilities)
        now_iso = now_iso or utcnow()
        conn = self.db._connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                "SELECT * FROM acquired_resources WHERE resource_id=?",
                (resource_id,),
            ).fetchone()
            if existing:
                decoded = self._decode(existing)
                if (
                    decoded.owner_role == owner_role
                    and decoded.kind == kind
                    and decoded.discovered_capabilities == discovered
                    and decoded.one_shot == bool(one_shot)
                ):
                    conn.commit()
                    return decoded
                raise ResourceCustodyError("RESOURCE_ID_CONFLICT", "resource id already names different custody")

            conn.execute(
                """INSERT INTO acquired_resources(
                   resource_id,owner_role,kind,status,
                   discovered_capabilities_json,resolved_capabilities_json,
                   authorized_capabilities_json,parent_capabilities_json,
                   activation_warrant_id,one_shot,acquired_at,resolved_at,
                   activated_at,consumed_at,expired_at,provenance_json,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    resource_id,
                    owner_role,
                    kind,
                    "quarantined",
                    json.dumps(discovered),
                    "[]",
                    "[]",
                    "[]",
                    None,
                    1 if one_shot else 0,
                    now_iso,
                    None,
                    None,
                    None,
                    None,
                    json.dumps(provenance or {}, sort_keys=True),
                    now_iso,
                ),
            )
            self._event(
                resource_id,
                "acquired",
                detail={
                    "status": "quarantined",
                    "discovered_capabilities": list(discovered),
                    "authority_granted": False,
                },
                now_iso=now_iso,
                conn=conn,
                commit=False,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        return self.get(resource_id)

    def resolve(
        self,
        resource_id: str,
        *,
        capabilities: Iterable[str],
        authenticated_evidence: dict[str, Any] | str,
        now_iso: str | None = None,
    ) -> AcquiredResource:
        if not authenticated_evidence:
            raise ResourceCustodyError("RESOLUTION_EVIDENCE_REQUIRED", "authenticated capability evidence is required")
        resolved = _caps(capabilities)
        now_iso = now_iso or utcnow()
        conn = self.db._connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM acquired_resources WHERE resource_id=?",
                (resource_id,),
            ).fetchone()
            if row is None:
                raise KeyError(resource_id)
            current = self._decode(row)
            if current.status == "resolved" and current.resolved_capabilities == resolved:
                conn.commit()
                return current
            if current.status != "quarantined":
                raise ResourceCustodyError(
                    "RESOURCE_NOT_QUARANTINED",
                    f"resource status={current.status} cannot be resolved",
                )
            conn.execute(
                """UPDATE acquired_resources
                   SET status='resolved',resolved_capabilities_json=?,
                       resolved_at=?,updated_at=?
                   WHERE resource_id=?""",
                (json.dumps(resolved), now_iso, now_iso, resource_id),
            )
            self._event(
                resource_id,
                "resolved",
                detail={
                    "resolved_capabilities": list(resolved),
                    "authenticated_evidence": authenticated_evidence,
                    "authority_granted": False,
                },
                now_iso=now_iso,
                conn=conn,
                commit=False,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        return self.get(resource_id)

    def _persisted_activation_warrant(self, resource_id: str, warrant_id: str, now_iso: str | None):
        warrant = self.db.get_temporal_warrant(warrant_id)
        if warrant is None:
            raise ResourceCustodyError(
                "ACTIVATION_WARRANT_NOT_PERSISTED",
                "resource custody cannot issue or infer its own activation warrant",
            )
        if not warrant.permits("activate_resource", "resource", resource_id, now_iso=now_iso):
            raise ResourceCustodyError(
                "ACTIVATION_WARRANT_INVALID",
                "persisted warrant does not currently authorize this resource activation",
            )
        return warrant

    def activate(
        self,
        resource_id: str,
        *,
        warrant_id: str,
        parent_capabilities: Iterable[str],
        now_iso: str | None = None,
    ) -> AcquiredResource:
        parent = _caps(parent_capabilities)
        now_iso = now_iso or utcnow()
        conn = self.db._connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM acquired_resources WHERE resource_id=?",
                (resource_id,),
            ).fetchone()
            if row is None:
                raise KeyError(resource_id)
            current = self._decode(row)
            if current.status == "activated":
                if current.activation_warrant_id == warrant_id and current.parent_capabilities == parent:
                    conn.commit()
                    return current
                raise ResourceCustodyError("RESOURCE_ALREADY_ACTIVATED", "resource already has an activation binding")
            if current.status != "resolved":
                raise ResourceCustodyError(
                    "RESOURCE_NOT_RESOLVED",
                    f"resource status={current.status} cannot be activated",
                )

            warrant = self._persisted_activation_warrant(resource_id, warrant_id, now_iso)
            resolved = set(current.resolved_capabilities)
            parent_set = set(parent)
            if not resolved.issubset(parent_set):
                blocked = sorted(resolved - parent_set)
                raise ResourceCustodyError(
                    "PARENT_SCOPE_WIDENING",
                    f"resolved capabilities exceed parent authority envelope: {blocked}",
                )

            scope_caps = _caps((warrant.scope or {}).get("capabilities") or ())
            if scope_caps and not resolved.issubset(set(scope_caps)):
                blocked = sorted(resolved - set(scope_caps))
                raise ResourceCustodyError(
                    "WARRANT_SCOPE_WIDENING",
                    f"resolved capabilities exceed activation warrant scope: {blocked}",
                )

            conn.execute(
                """UPDATE acquired_resources
                   SET status='activated',authorized_capabilities_json=?,
                       parent_capabilities_json=?,activation_warrant_id=?,
                       activated_at=?,updated_at=?
                   WHERE resource_id=?""",
                (
                    json.dumps(sorted(resolved)),
                    json.dumps(parent),
                    warrant_id,
                    now_iso,
                    now_iso,
                    resource_id,
                ),
            )
            self._event(
                resource_id,
                "activated",
                detail={
                    "warrant_id": warrant_id,
                    "authorized_capabilities": sorted(resolved),
                    "parent_capabilities": list(parent),
                    "authority_source": "persisted_temporal_warrant",
                },
                now_iso=now_iso,
                conn=conn,
                commit=False,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        return self.get(resource_id)

    def _assert_usable_row(
        self,
        current: AcquiredResource,
        capability: str,
        *,
        now_iso: str | None,
    ) -> None:
        if current.status != "activated":
            raise ResourceCustodyError(
                "RESOURCE_NOT_ACTIVE",
                f"resource status={current.status} is not executable",
            )
        capability = str(capability).strip()
        if capability not in set(current.authorized_capabilities):
            raise ResourceCustodyError(
                "CAPABILITY_NOT_AUTHORIZED",
                f"capability {capability!r} was not activated for resource",
            )
        if not current.activation_warrant_id:
            raise ResourceCustodyError("ACTIVATION_WARRANT_MISSING", "active resource has no warrant binding")
        self._persisted_activation_warrant(
            current.resource_id,
            current.activation_warrant_id,
            now_iso,
        )

    def assert_usable(
        self,
        resource_id: str,
        capability: str,
        *,
        now_iso: str | None = None,
    ) -> AcquiredResource:
        current = self.get(resource_id)
        self._assert_usable_row(current, capability, now_iso=now_iso)
        self._event(
            resource_id,
            "use_checked",
            detail={"capability": capability, "warrant_revalidated": True},
            now_iso=now_iso,
        )
        return current

    def reserve_one_shot_use(
        self,
        resource_id: str,
        capability: str,
        *,
        now_iso: str | None = None,
    ) -> AcquiredResource:
        """Spend a one-shot resource before the irreversible external effect.

        A crash after this commit leaves the resource consumed.  Recovery must
        reconcile or acquire fresh authority; it may not replay the old use.
        """
        now_iso = now_iso or utcnow()
        conn = self.db._connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM acquired_resources WHERE resource_id=?",
                (resource_id,),
            ).fetchone()
            if row is None:
                raise KeyError(resource_id)
            current = self._decode(row)
            if not current.one_shot:
                raise ResourceCustodyError(
                    "RESOURCE_NOT_ONE_SHOT",
                    "reserve_one_shot_use applies only to one-shot resources",
                )
            self._assert_usable_row(current, capability, now_iso=now_iso)
            conn.execute(
                """UPDATE acquired_resources
                   SET status='consumed',consumed_at=?,updated_at=?
                   WHERE resource_id=?""",
                (now_iso, now_iso, resource_id),
            )
            self._event(
                resource_id,
                "use_reserved",
                detail={
                    "capability": capability,
                    "warrant_revalidated": True,
                    "authority_consumed_before_effect": True,
                },
                now_iso=now_iso,
                conn=conn,
                commit=False,
            )
            self._event(
                resource_id,
                "consumed",
                detail={"reason": "one_shot_use_reserved"},
                now_iso=now_iso,
                conn=conn,
                commit=False,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        return self.get(resource_id)

    def expire(
        self,
        resource_id: str,
        *,
        reason: str,
        now_iso: str | None = None,
    ) -> AcquiredResource:
        if not str(reason).strip():
            raise ResourceCustodyError("EXPIRY_REASON_REQUIRED", "expiry reason is required")
        now_iso = now_iso or utcnow()
        conn = self.db._connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM acquired_resources WHERE resource_id=?",
                (resource_id,),
            ).fetchone()
            if row is None:
                raise KeyError(resource_id)
            current = self._decode(row)
            if current.status == "expired":
                conn.commit()
                return current
            if current.status == "consumed":
                raise ResourceCustodyError("TERMINAL_RESOURCE", "consumed resource cannot transition to expired")
            conn.execute(
                """UPDATE acquired_resources
                   SET status='expired',expired_at=?,updated_at=?
                   WHERE resource_id=?""",
                (now_iso, now_iso, resource_id),
            )
            self._event(
                resource_id,
                "expired",
                detail={"reason": reason},
                now_iso=now_iso,
                conn=conn,
                commit=False,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        return self.get(resource_id)

    def list_events(self, resource_id: str) -> list[dict[str, Any]]:
        rows = self.db._connection().execute(
            """SELECT * FROM acquired_resource_events
               WHERE resource_id=? ORDER BY occurred_at,event_id""",
            (resource_id,),
        ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["detail"] = json.loads(item.pop("detail_json") or "{}")
            out.append(item)
        return out
