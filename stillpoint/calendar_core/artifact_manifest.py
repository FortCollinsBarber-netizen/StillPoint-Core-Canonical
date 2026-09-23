from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .projection_vectors import (
    PROJECTION_VECTOR_VERSION,
    build_calendar_projection_vectors,
)
from .sacred_map import MAP_VERSION, build_sacred_civic_map
from .spec import SPEC_VERSION, build_calendar_core_spec

ARTIFACT_MANIFEST_VERSION = "stillpoint-calendar-artifact-manifest-v2-fixed-364"


def canonical_export_bytes(document: dict[str, Any]) -> bytes:
    return (
        json.dumps(document, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def build_calendar_core_artifact_manifest() -> dict[str, Any]:
    artifacts = (
        (
            "stillpoint/contracts/calendar_core_spec.json",
            "calendar-law",
            SPEC_VERSION,
            build_calendar_core_spec(),
        ),
        (
            "stillpoint/contracts/calendar_projection_vectors.json",
            "conformance-proof-only",
            PROJECTION_VECTOR_VERSION,
            build_calendar_projection_vectors(),
        ),
        (
            "stillpoint/contracts/calendar_sacred_civic_map.json",
            "sacred-civic-map",
            MAP_VERSION,
            build_sacred_civic_map(),
        ),
    )
    rows = []
    for path, role, version, document in artifacts:
        payload = canonical_export_bytes(document)
        rows.append(
            {
                "path": path,
                "role": role,
                "version": version,
                "sha256": sha256_hex(payload),
                "bytes": len(payload),
            }
        )

    return {
        "version": ARTIFACT_MANIFEST_VERSION,
        "authorityStatus": "custody-only",
        "artifacts": rows,
        "compatibilityBridge": {
            "path": "stillpoint/contracts/calendar_core_contract.json",
            "authorityStatus": "historical-compatibility-only",
            "includedInManifestDigest": False,
        },
        "invariants": [
            "law-map-and-proof-have-distinct-roles",
            "fixed-grid-has-no-reconciliation-days",
            "december-31-does-not-exist",
            "day-364-directly-precedes-next-day-001",
            "proof-vectors-have-no-independent-authority",
        ],
    }


def export_calendar_core_artifact_manifest(path: Path) -> None:
    path.write_bytes(
        canonical_export_bytes(
            build_calendar_core_artifact_manifest()
        )
    )
