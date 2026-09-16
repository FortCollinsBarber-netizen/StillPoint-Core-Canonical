from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from ..contracts.models import ActionEvidence, ActionRequest, ActionResult


class OutboxBoundaryError(RuntimeError):
    pass


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_segment(value: str, *, label: str) -> str:
    value=(value or "").strip()
    if not value:
        raise OutboxBoundaryError(f"{label} required")
    p=Path(value)
    if p.is_absolute() or value in {".",".."} or ".." in p.parts:
        raise OutboxBoundaryError(f"unsafe {label}")
    if "/" in value or "\\" in value:
        raise OutboxBoundaryError(f"unsafe {label}")
    if not re.fullmatch(r"[A-Za-z0-9._ -]+", value):
        raise OutboxBoundaryError(f"unsupported characters in {label}")
    return value


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.is_symlink():
        raise OutboxBoundaryError("destination is a symlink")
    fd,tmp_name=tempfile.mkstemp(prefix=".stillpoint-", dir=str(path.parent))
    tmp=Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(str(tmp), str(path))
        try:
            dir_fd=os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass
    finally:
        if tmp.exists():
            tmp.unlink()


class BoundedOutboxAdapter:
    name="bounded_outbox"
    action_types=("export_artifact",)

    def __init__(self, *, db, outbox_root: Path, enabled: bool=False):
        self.db=db
        self.enabled=bool(enabled)
        root=Path(outbox_root).expanduser()
        if not root.is_absolute():
            raise OutboxBoundaryError("outbox root must be an absolute path")
        if root.exists() and root.is_symlink():
            raise OutboxBoundaryError("outbox root may not be a symlink")
        self.outbox_root=root.resolve(strict=False)

    def _validate_bound_root(self, request: ActionRequest) -> None:
        expected=str(self.outbox_root)
        if request.target != "bounded_outbox:"+expected:
            raise OutboxBoundaryError("configured outbox root does not match authorized target")
        if "outbox_root="+expected not in request.scope:
            raise OutboxBoundaryError("configured outbox root is outside authorized scope")

    def _source(self, request: ActionRequest):
        if request.action_type != "export_artifact":
            raise OutboxBoundaryError("unsupported action type")
        if len(request.artifact_refs) != 1:
            raise OutboxBoundaryError("bounded outbox requires exactly one authorized artifact")
        ref=request.artifact_refs[0]
        if not ref.artifact_id:
            raise OutboxBoundaryError("artifact id required")
        row=self.db.get_artifact(ref.artifact_id)
        if not row:
            raise OutboxBoundaryError("artifact not found")
        if row["task_id"] != request.task_id:
            raise OutboxBoundaryError("artifact task mismatch")
        if int(row["version"]) != int(ref.version):
            raise OutboxBoundaryError("artifact version mismatch")
        if row["sha256"] != ref.sha256:
            raise OutboxBoundaryError("artifact metadata hash mismatch")
        run=self.db.get_run(row["produced_by_run_id"])
        if not run:
            raise OutboxBoundaryError("artifact source run not found")
        data=str(run["output"]).encode("utf-8")
        if _sha(data) != ref.sha256:
            raise OutboxBoundaryError("artifact content hash mismatch")
        return ref,row,data

    def can_execute(self, request: ActionRequest) -> bool:
        if not self.enabled or request.action_type not in self.action_types:
            return False
        try:
            self._validate_bound_root(request)
            ref,_,_=self._source(request)
            _safe_segment(request.action_id,label="action id")
            _safe_segment(ref.name,label="artifact name")
        except Exception:
            return False
        return True

    def _paths(self, request: ActionRequest):
        action_id=_safe_segment(request.action_id,label="action id")
        name=_safe_segment(request.artifact_refs[0].name,label="artifact name")
        root=self.outbox_root
        if root.exists() and root.is_symlink():
            raise OutboxBoundaryError("outbox root may not be a symlink")
        root.mkdir(parents=True,exist_ok=True)
        root=root.resolve()
        action_dir=root/action_id
        if action_dir.exists() and action_dir.is_symlink():
            raise OutboxBoundaryError("action outbox may not be a symlink")
        action_dir.mkdir(parents=True,exist_ok=True)
        action_dir=action_dir.resolve()
        if action_dir != root and root not in action_dir.parents:
            raise OutboxBoundaryError("action path escaped outbox root")
        destination=action_dir/name
        receipt=action_dir/"_receipt.json"
        if destination.resolve(strict=False).parent != action_dir:
            raise OutboxBoundaryError("destination escaped action outbox")
        return root,action_dir,destination,receipt

    def execute(self, request: ActionRequest) -> ActionResult:
        if not self.enabled:
            raise OutboxBoundaryError("bounded outbox adapter is disabled")
        if not request.warrant_id:
            raise OutboxBoundaryError("bound warrant required")
        if request.approval_required and not request.approval_id:
            raise OutboxBoundaryError("approval required")
        if not request.permitted():
            raise OutboxBoundaryError("approval or warrant expired")

        self._validate_bound_root(request)
        ref,_,data=self._source(request)
        root,_,destination,receipt_path=self._paths(request)
        content_hash=_sha(data)

        payload={
            "schema":"stillpoint.outbox-receipt.v1",
            "action_id":request.action_id,
            "warrant_id":request.warrant_id,
            "approval_id":request.approval_id,
            "idempotency_key":request.idempotency_key,
            "adapter":self.name,
            "task_id":request.task_id,
            "authorized_target":request.target,
            "artifact":{
                "artifact_id":ref.artifact_id,
                "name":ref.name,
                "kind":ref.kind,
                "version":ref.version,
                "sha256":ref.sha256,
            },
            "destination":str(destination.relative_to(root)),
            "content_sha256":content_hash,
        }
        canonical=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
        payload["result_hash"]=_sha(canonical)
        receipt_bytes=(json.dumps(payload,sort_keys=True,indent=2,ensure_ascii=False)+"\n").encode("utf-8")

        if receipt_path.exists():
            if receipt_path.is_symlink():
                raise OutboxBoundaryError("receipt is a symlink")
            try:
                prior=json.loads(receipt_path.read_text("utf-8"))
            except Exception as exc:
                raise OutboxBoundaryError("existing receipt is unreadable") from exc
            if prior != payload:
                raise OutboxBoundaryError("conflicting receipt already exists")
            if not destination.is_file() or destination.is_symlink():
                raise OutboxBoundaryError("receipt exists without a safe destination")
            if _sha(destination.read_bytes()) != content_hash:
                raise OutboxBoundaryError("existing export conflicts with receipt")
            receipt_hash=_sha(receipt_path.read_bytes())
            return ActionResult(
                action_id=request.action_id,
                status="succeeded",
                evidence=[ActionEvidence(
                    type="export_receipt",
                    sha256=receipt_hash,
                    note=str(receipt_path.relative_to(root)),
                    satisfies="export_receipt",
                )],
                adapter=self.name,
                external_id=str(destination.relative_to(root)),
            )

        if destination.exists():
            raise OutboxBoundaryError("pre-existing destination has no matching StillPoint receipt")

        _atomic_write(destination,data)
        if destination.is_symlink() or not destination.is_file():
            raise OutboxBoundaryError("export destination verification failed")
        if _sha(destination.read_bytes()) != content_hash:
            raise OutboxBoundaryError("exported artifact hash mismatch")

        _atomic_write(receipt_path,receipt_bytes)
        receipt_hash=_sha(receipt_path.read_bytes())

        return ActionResult(
            action_id=request.action_id,
            status="succeeded",
            evidence=[ActionEvidence(
                type="export_receipt",
                sha256=receipt_hash,
                note=str(receipt_path.relative_to(root)),
                satisfies="export_receipt",
            )],
            adapter=self.name,
            external_id=str(destination.relative_to(root)),
        )
