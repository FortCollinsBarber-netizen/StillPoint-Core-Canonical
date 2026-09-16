from __future__ import annotations

import os
from pathlib import Path

from .outbox import BoundedOutboxAdapter
from .registry import ActionAdapterRegistry


class ProductionBoundaryConfigurationError(RuntimeError):
    pass


def _enabled() -> bool:
    return os.getenv("STILLPOINT_ENABLE_OUTBOX","0").strip()=="1"


def configured_outbox_root() -> Path:
    raw=os.getenv("STILLPOINT_OUTBOX_ROOT","").strip()
    if not raw:
        raise ProductionBoundaryConfigurationError(
            "export_artifact requires STILLPOINT_OUTBOX_ROOT before authorization"
        )
    path=Path(raw).expanduser()
    if not path.is_absolute():
        raise ProductionBoundaryConfigurationError(
            "STILLPOINT_OUTBOX_ROOT must be an absolute path"
        )
    if path.exists() and path.is_symlink():
        raise ProductionBoundaryConfigurationError(
            "STILLPOINT_OUTBOX_ROOT may not be a symlink"
        )
    return path.resolve(strict=False)


def inspect_production_adapters() -> dict:
    if not _enabled():
        data={
            "ok":True,
            "enabled":[],
            "available_disabled":["bounded_outbox"],
            "note":"bounded_outbox is production-capable but disabled by default",
        }
        raw=os.getenv("STILLPOINT_OUTBOX_ROOT","").strip()
        if raw:
            try:
                data["configured_outbox_root"]=str(configured_outbox_root())
            except Exception as exc:
                data["configuration_warning"]=str(exc)
        return data
    try:
        root=configured_outbox_root()
    except Exception as exc:
        return {
            "ok":False,
            "enabled":[],
            "available_disabled":["bounded_outbox"],
            "error":str(exc),
        }
    return {
        "ok":True,
        "enabled":["bounded_outbox"],
        "outbox_root":str(root),
        "note":"bounded local artifact export only; no network adapter enabled",
    }


def build_production_registry(runtime) -> ActionAdapterRegistry:
    status=inspect_production_adapters()
    if not status["ok"]:
        raise ProductionBoundaryConfigurationError(
            status.get("error") or "invalid production adapter configuration"
        )
    adapters=[]
    if "bounded_outbox" in status["enabled"]:
        adapters.append(BoundedOutboxAdapter(
            db=runtime.db,
            outbox_root=Path(status["outbox_root"]),
            enabled=True,
        ))
    return ActionAdapterRegistry(adapters)
