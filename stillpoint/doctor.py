"""Release/installation doctor for StillPoint Core.

The doctor distinguishes install health from release health. A runtime-only wheel
may be healthy without evaluator assets, while a source checkout may not claim a
release checkpoint if migration mirrors, frozen corpora, checkpoint metadata, or
unresolved external dispatches are inconsistent.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


_MIGRATION_RE = re.compile(r"^(\d{3})_.*\.sql$")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _migration_versions(path: Path) -> list[int]:
    versions=[]
    for item in path.glob("*.sql"):
        match=_MIGRATION_RE.match(item.name)
        if match:
            versions.append(int(match.group(1)))
    return sorted(versions)


def _mirror_check(canonical: Path, packaged: Path) -> dict[str, Any]:
    cfiles=sorted(canonical.glob("*.sql"))
    pfiles=sorted(packaged.glob("*.sql"))
    cnames=[p.name for p in cfiles]
    pnames=[p.name for p in pfiles]
    if cnames != pnames:
        return {
            "ok": False,
            "canonical": cnames,
            "packaged": pnames,
            "error": "migration mirror filename mismatch",
        }
    mismatches=[]
    for c,p in zip(cfiles,pfiles):
        if _sha256(c) != _sha256(p):
            mismatches.append(c.name)
    return {
        "ok": not mismatches,
        "files": cnames,
        "mismatches": mismatches,
    }


def run_doctor(*, root: Path, db, registry) -> dict[str, Any]:
    root=Path(root).resolve()
    package_root=Path(__file__).resolve().parent
    source_checkout=(root/"pyproject.toml").is_file() or (root/".git").exists()

    checks: dict[str, Any]={}

    canonical_migrations=root/"migrations"
    packaged_migrations=package_root/"migrations"
    if source_checkout:
        mirror=_mirror_check(canonical_migrations, packaged_migrations)
        checks["migration_mirror"]=mirror
        versions=_migration_versions(canonical_migrations)
    else:
        versions=_migration_versions(packaged_migrations)
        checks["migration_mirror"]={
            "ok": bool(versions),
            "runtime_only": True,
            "files": [p.name for p in sorted(packaged_migrations.glob("*.sql"))],
        }

    latest=max(versions) if versions else 0
    try:
        schema=db.schema_version
        checks["database"]={
            "ok": bool(latest) and schema == latest,
            "schema_version": schema,
            "latest_migration": latest,
        }
    except Exception as exc:
        checks["database"]={"ok":False,"error":str(exc),"latest_migration":latest}

    try:
        checks["agent_registry"]={
            "ok": True,
            "agents": registry.ids(),
        }
    except Exception as exc:
        checks["agent_registry"]={"ok":False,"error":str(exc)}

    try:
        from .capability_fabric import CapabilityBroker, capability_manifest_path
        broker=CapabilityBroker(db,capability_manifest_path(root))
        broker.sync_manifest()
        checks["capability_fabric"]=broker.audit_manifest()
    except Exception as exc:
        checks["capability_fabric"]={"ok":False,"error":str(exc)}

    if source_checkout:
        canonical_agents=root/"config"/"agents.json"
        packaged_agents=package_root/"defaults"/"agents.json"
        if canonical_agents.is_file() and packaged_agents.is_file():
            checks["agent_registry_mirror"]={
                "ok": canonical_agents.read_bytes() == packaged_agents.read_bytes()
            }
        else:
            checks["agent_registry_mirror"]={
                "ok":False,
                "error":"canonical or packaged agents.json missing",
            }

        canonical_capabilities=root/"config"/"capabilities.json"
        packaged_capabilities=package_root/"defaults"/"capabilities.json"
        if canonical_capabilities.is_file() and packaged_capabilities.is_file():
            checks["capability_manifest_mirror"]={
                "ok": canonical_capabilities.read_bytes() == packaged_capabilities.read_bytes()
            }
        else:
            checks["capability_manifest_mirror"]={
                "ok":False,
                "error":"canonical or packaged capabilities.json missing",
            }

        try:
            from eval.frozen import verify_frozen_corpora
            hashes=verify_frozen_corpora()
            checks["frozen_corpora"]={"ok":True,"hashes":hashes}
        except Exception as exc:
            checks["frozen_corpora"]={"ok":False,"error":str(exc)}

        checkpoint=root/"CHECKPOINT.json"
        if checkpoint.is_file():
            try:
                raw=json.loads(checkpoint.read_text(encoding="utf-8"))
                cp_schema=int(raw.get("schema_version", -1))
                checks["checkpoint"]={
                    "ok": cp_schema == latest,
                    "schema_version": cp_schema,
                    "expected_schema_version": latest,
                    "version": raw.get("version"),
                    "milestone": raw.get("last_completed_milestone"),
                }
            except Exception as exc:
                checks["checkpoint"]={"ok":False,"error":str(exc)}
        else:
            checks["checkpoint"]={
                "ok":False,
                "error":"CHECKPOINT.json missing from source checkout",
            }

        transfer=root/"transfer"
        transfer_files=(
            [p.name for p in transfer.iterdir()]
            if transfer.exists() and transfer.is_dir()
            else []
        )
        checks["staging_residue"]={
            "ok": not transfer_files,
            "files": transfer_files,
        }
    else:
        checks["capability_manifest_mirror"]={
            "ok":True,
            "runtime_only":True,
            "note":"runtime-only wheel uses packaged capability manifest",
        }
        checks["frozen_corpora"]={
            "ok":True,
            "runtime_only":True,
            "note":"evaluator assets are not required in runtime-only wheel",
        }
        checks["checkpoint"]={
            "ok":True,
            "runtime_only":True,
            "note":"release checkpoint is source metadata",
        }
        checks["staging_residue"]={"ok":True,"runtime_only":True}

    try:
        unresolved=db.list_unresolved_dispatches()
        checks["unresolved_dispatches"]={
            "ok": len(unresolved) == 0,
            "count": len(unresolved),
            "action_ids": [row["action_id"] for row in unresolved],
            "note":"unresolved external dispatches block release readiness",
        }
    except Exception as exc:
        checks["unresolved_dispatches"]={"ok":False,"error":str(exc)}

    try:
        from .adapters.production import inspect_production_adapters
        checks["production_external_adapters"]=inspect_production_adapters()
    except Exception as exc:
        checks["production_external_adapters"]={"ok":False,"enabled":[],"error":str(exc)}

    checks["overall_ok"]=all(
        value.get("ok",False)
        for value in checks.values()
        if isinstance(value,dict)
    )
    return checks
