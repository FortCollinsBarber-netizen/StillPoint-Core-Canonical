#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()

def replace_once(path, old, new):
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected anchor once, found {count}\n--- looking for ---\n{old[:200]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")

# 1. ActionRequest.warrant_id + permitted requires warrant
replace_once(
    ROOT/"stillpoint/contracts/models.py",
    '    authority_revision: str = ""\n\n    def permitted(self, now_iso: str | None = None) -> bool:\n        if not self.approval_required:\n            return True\n',
    '    authority_revision: str = ""\n    warrant_id: str | None = None\n\n    def permitted(self, now_iso: str | None = None) -> bool:\n        if not self.warrant_id:\n            return False\n        if not self.approval_required:\n            return True\n',
)

# 2. DB methods — only the NEW gate methods (add/get already exist)
db_methods = '''
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
        row = self._connection().execute(
            "SELECT COUNT(*) FROM action_warrant_consumptions WHERE warrant_id=?",
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
                "SELECT warrant_id,authority_revision,approval_id FROM action_requests WHERE id=?",
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
        if disposition not in {"reserved", "completed", "failed", "uncertain"}:
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

'''
replace_once(
    ROOT/"stillpoint/db.py",
    '    def set_task_budget(self, task_id: str, limits) -> None:\n',
    db_methods + '    def set_task_budget(self, task_id: str, limits) -> None:\n',
)

# 3. runtime imports
replace_once(
    ROOT/"stillpoint/runtime.py",
    'from .registry import AgentRegistry\n',
    'from .registry import AgentRegistry\nfrom .temporal.action_gate import build_ceo_warrant, validate_bound_warrant\nfrom .temporal.firewall import TemporalAuthorityError\n',
)

# 4. _request_from_row includes warrant_id
replace_once(
    ROOT/"stillpoint/runtime.py",
    'click_irreversible=bool(row["click_irreversible"]),authority_revision=row["authority_revision"])\n',
    'click_irreversible=bool(row["click_irreversible"]),authority_revision=row["authority_revision"],warrant_id=row["warrant_id"] if "warrant_id" in row.keys() else None)\n',
)

# 5. execute_action: warrant gate before dispatch
replace_once(
    ROOT/"stillpoint/runtime.py",
    '        req=self._request_from_row(row)\n        if req.approval_required and (not req.permitted(now_iso or _now_dt().isoformat()) or not self.db.has_action_approval(req.action_id,req.approval_id)):\n            raise NotAuthorized("missing, expired, or mismatched approval")\n        latest=self._latest_artifact_map(req.task_id)\n',
    '        req=self._request_from_row(row)\n        effective_now=now_iso or _now_dt().isoformat()\n        if req.approval_required and (not req.permitted(effective_now) or not self.db.has_action_approval(req.action_id,req.approval_id)):\n            raise NotAuthorized("missing, expired, mismatched approval, or warrant")\n        if not req.warrant_id:\n            raise NotAuthorized("consequential action has no bound warrant")\n        warrant=self.db.get_temporal_warrant(req.warrant_id)\n        if not warrant:\n            raise NotAuthorized("bound warrant does not exist")\n        try:\n            validate_bound_warrant(\n                request=req,\n                warrant=warrant,\n                now_iso=effective_now,\n                actions_used=self.db.count_warrant_consumptions(req.warrant_id),\n            )\n        except TemporalAuthorityError as exc:\n            raise NotAuthorized(str(exc)) from exc\n        latest=self._latest_artifact_map(req.task_id)\n',
)

# 6. reserve before adapter, disposition after
replace_once(
    ROOT/"stillpoint/runtime.py",
    '        result=adapter_registry.execute(req)\n        self.db.add_action_result(result)\n        status=runtime_complete(req,result,now_iso=now_iso)\n        self.db.update_action_request_status(action_id,status)\n',
    '        self.db.reserve_warrant_for_action(\n            action_id=req.action_id,\n            warrant_id=req.warrant_id,\n            authority_revision=req.authority_revision,\n            approval_id=req.approval_id,\n            artifact_hashes=[ref.sha256 for ref in req.artifact_refs],\n        )\n        try:\n            result=adapter_registry.execute(req)\n        except Exception:\n            self.db.set_warrant_consumption_disposition(req.action_id,"uncertain")\n            raise\n        self.db.add_action_result(result)\n        status=runtime_complete(req,result,now_iso=now_iso)\n        self.db.update_action_request_status(action_id,status)\n        if status=="completed":\n            self.db.set_warrant_consumption_disposition(req.action_id,"completed")\n            self.db.complete_temporal_warrant(req.warrant_id)\n        else:\n            self.db.set_warrant_consumption_disposition(req.action_id,"failed")\n',
)

# 7. approve issues and binds CEO warrant
replace_once(
    ROOT/"stillpoint/runtime.py",
    '        approval=self.db.add_approval(task_id,"approved",note)\n        for r in requests:self.db.bind_action_approval(r["id"],approval)\n        self.db.update_task(task_id,status="ready_for_action",approval_reason="")\n',
    '        approval=self.db.add_approval(task_id,"approved",note)\n        for r in requests:\n            self.db.bind_action_approval(r["id"],approval)\n            refreshed=self.db.get_action_request(r["id"])\n            req=self._request_from_row(refreshed)\n            req.approval_id=approval\n            warrant=build_ceo_warrant(request=req,approval_id=approval)\n            self.db.insert_temporal_warrant(warrant)\n            self.db.bind_action_warrant(req.action_id,warrant.warrant_id)\n        self.db.update_task(task_id,status="ready_for_action",approval_reason="")\n',
)

print("Patch 002 source edits applied successfully.")
