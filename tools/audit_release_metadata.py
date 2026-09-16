#!/usr/bin/env python3
# Fail-closed audit for StillPoint canonical release identity and custody metadata.

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()

EXPECTED_VERSION = "0.2.0rc1"
EXPECTED_REPOSITORY = "FortCollinsBarber-netizen/StillPoint-Core-Canonical"
EXPECTED_SCHEMA = 9
EXPECTED_TAGS = {
    "patch005-source-tree": "0c0885d7dfe88fa4f70ae265b180af4bca6945c6",
    "patch005-canonical": "4a077f216902f4bad725b6b2e61a176a54f81404",
}

errors = []

def require(condition, message):
    if not condition:
        errors.append(message)

def read_project_version(path):
    in_project = False
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            in_project = line == "[project]"
            continue
        if in_project and line.startswith("version"):
            match = re.match(r'version\s*=\s*"([^"]+)"\s*$', line)
            if match:
                return match.group(1)
    return None

project_version = read_project_version(ROOT / "pyproject.toml")

init_text = (ROOT / "stillpoint" / "__init__.py").read_text()
match = re.search(r'__version__\s*=\s*"([^"]+)"', init_text)
runtime_version = match.group(1) if match else None

checkpoint = json.loads((ROOT / "CHECKPOINT.json").read_text())
manifest = json.loads((ROOT / "RELEASE_MANIFEST.json").read_text())

require(project_version == EXPECTED_VERSION, "pyproject version mismatch: %r" % (project_version,))
require(runtime_version == EXPECTED_VERSION, "runtime version mismatch: %r" % (runtime_version,))
require(checkpoint.get("version") == EXPECTED_VERSION, "checkpoint version mismatch: %r" % checkpoint.get("version"))
require(manifest.get("version") == EXPECTED_VERSION, "manifest version mismatch: %r" % manifest.get("version"))
require(checkpoint.get("schema_version") == EXPECTED_SCHEMA, "checkpoint schema mismatch: %r" % checkpoint.get("schema_version"))
require(manifest.get("schema_version") == EXPECTED_SCHEMA, "manifest schema mismatch: %r" % manifest.get("schema_version"))
require(checkpoint.get("known_runtime_defects") == [], "known runtime defects are not empty")
require(
    checkpoint.get("external_action_adapters", {}).get("production_enabled") == [],
    "production external adapters are enabled in checkpoint",
)
require(
    manifest.get("release_invariants", {}).get("production_external_adapters_enabled") == [],
    "production external adapters are enabled in release manifest",
)
require(
    checkpoint.get("release_candidate", {}).get("canonical_repository") == EXPECTED_REPOSITORY,
    "checkpoint canonical repository mismatch",
)
require(manifest.get("canonical_repository") == EXPECTED_REPOSITORY, "manifest canonical repository mismatch")
require(manifest.get("runtime_capability_change") is False, "Patch 006 must remain capability-neutral")

github_repository = os.environ.get("GITHUB_REPOSITORY")
if github_repository:
    require(github_repository == EXPECTED_REPOSITORY, "CI repository mismatch: %s" % github_repository)

for tag, expected_commit in EXPECTED_TAGS.items():
    try:
        actual = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-list", "-n", "1", tag],
            universal_newlines=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except subprocess.CalledProcessError as exc:
        errors.append("cannot resolve provenance tag %s: %s" % (tag, exc.output.strip()))
        continue
    require(actual == expected_commit, "%s mismatch: expected %s, got %s" % (tag, expected_commit, actual))

if errors:
    for error in errors:
        print("FAIL", error)
    raise SystemExit(1)

print("Release metadata audit passed.")
print("version:", EXPECTED_VERSION)
print("repository:", EXPECTED_REPOSITORY)
print("schema:", EXPECTED_SCHEMA)
for tag, commit in EXPECTED_TAGS.items():
    print("%s: %s" % (tag, commit))
