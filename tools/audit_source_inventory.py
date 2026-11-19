"""Deterministic, offline inventory of a Git checkout; never executes repository code.

Usage: python tools/audit_source_inventory.py --repo . > local_inventory.json
Keep inventory output from private repositories private.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

CODE_SUFFIXES = frozenset({".py", ".swift", ".js", ".ts", ".html", ".css", ".sh", ".sql", ".toml", ".yml", ".yaml"})
SENSITIVE_PATH = re.compile(r"(?:authority|warrant|secret|credential|adapter|migration|workflow|provider|deploy|release|entitlement)", re.I)
REVIEW_MARKER = re.compile(r"\b(?:TODO|FIXME|HACK|XXX)\b")


def inventory(repo: Path) -> dict:
    root = repo.resolve(strict=True)
    completed = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--cached", "-z", "--full-name"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    names = sorted(item.decode("utf-8", "surrogateescape") for item in completed.stdout.split(b"\0") if item)
    rows = []
    for name in names:
        target = root / name
        row = {"path": name, "review_status": "NOT_READ", "priority": "review_first" if SENSITIVE_PATH.search(name) else "routine"}
        if target.is_symlink():
            row.update(kind="symlink", sha256=None, bytes=None, physical_lines=None, review_markers=None)
        elif not target.is_file():
            row.update(kind="missing_worktree_file", sha256=None, bytes=None, physical_lines=None, review_markers=None)
        else:
            data = target.read_bytes()
            kind = "code_or_config" if target.suffix.lower() in CODE_SUFFIXES else "other"
            try:
                decoded = data.decode("utf-8") if b"\0" not in data else None
            except UnicodeDecodeError:
                decoded = None
            lines = data.count(b"\n") + int(bool(data) and not data.endswith(b"\n")) if decoded is not None else None
            row.update(kind=kind if decoded is not None else "binary_or_non_utf8",
                       sha256=hashlib.sha256(data).hexdigest(), bytes=len(data),
                       physical_lines=lines,
                       review_markers=len(REVIEW_MARKER.findall(decoded)) if decoded is not None else None)
        rows.append(row)
    return {"schema": "stillpoint-offline-inventory-v1", "root": str(root),
            "tracked_file_count": len(rows),
            "code_or_config_count": sum(x["kind"] == "code_or_config" for x in rows),
            "not_read_count": len(rows),
            "files": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    args = parser.parse_args()
    try:
        report = inventory(args.repo)
    except (OSError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f"Cannot inventory repository: {exc}\n")
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
