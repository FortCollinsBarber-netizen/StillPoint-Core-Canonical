from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .projection_vectors import (
    PROJECTION_VECTOR_VERSION,
    build_calendar_projection_vectors,
)
from .spec import (
    SPEC_VERSION,
    build_calendar_core_spec,
)

ARTIFACT_MANIFEST_VERSION = "stillpoint-calendar-artifact-manifest-v1"


def canonical_export_bytes(document: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            document,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def build_calendar_core_artifact_manifest() -> dict[str, Any]:
    spec_bytes = canonical_export_bytes(
        build_calendar_core_spec()
    )
    vector_bytes = canonical_export_bytes(
        build_calendar_projection_vectors()
    )

    return {
        "version": ARTIFACT_MANIFEST_VERSION,
        "authorityStatus": "custody-only",
        "artifacts": [
            {
                "path":
                    "stillpoint/contracts/calendar_core_spec.json",
                "role": "calendar-law",
                "version": SPEC_VERSION,
                "sha256": sha256_hex(spec_bytes),
                "bytes": len(spec_bytes),
            },
            {
                "path":
                    "stillpoint/contracts/calendar_projection_vectors.json",
                "role": "conformance-proof-only",
                "version": PROJECTION_VECTOR_VERSION,
                "sha256": sha256_hex(vector_bytes),
                "bytes": len(vector_bytes),
            },
        ],
        "compatibilityBridge": {
            "path":
                "stillpoint/contracts/calendar_core_contract.json",
            "authorityStatus": "non-authoritative-compatibility-only",
            "includedInManifestDigest": False,
        },
        "invariants": [
            "law-and-proof-have-distinct-roles",
            "proof-vectors-have-no-civic-authority",
            "manifest-does-not-ratify-projection-epoch",
            "compatibility-bridge-is-not-constitutional-law",
            "no-reconciliation-artifact-has-operative-authority",
        ],
    }


def export_calendar_core_artifact_manifest(
    path: Path,
) -> None:
    path.write_bytes(
        canonical_export_bytes(
            build_calendar_core_artifact_manifest()
        )
    )
