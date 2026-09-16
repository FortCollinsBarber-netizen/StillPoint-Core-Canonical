#!/usr/bin/env python3
"""Repository-wide audit for consequential action bypasses.

The script is intentionally simple and deterministic. It scans Python AST for:
- ActionRequest(...) construction
- add_action_request(...) calls
- adapter.execute(...) / execute_resolved(...) calls
- direct INSERT/UPDATE strings touching action_requests

It exits nonzero when a production-path occurrence is outside the explicit allowlist.
Tests are reported but do not fail the audit.
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()

ALLOW_ACTIONREQUEST = {
    "stillpoint/runtime.py",
}
ALLOW_ADD_ACTION = {
    "stillpoint/runtime.py",
}
ALLOW_ADAPTER_EXECUTION = {
    "stillpoint/runtime.py",
    "stillpoint/adapters/registry.py",
}
ALLOW_ACTION_SQL = {
    "stillpoint/db.py",
    "stillpoint/runtime.py",  # authorize_reentry binds trigger/parent columns only
}

findings=[]

for path in sorted(ROOT.rglob("*.py")):
    rel=path.relative_to(ROOT).as_posix()
    if any(part in {".git",".venv","venv","__pycache__","build","dist"} for part in path.parts):
        continue
    try:
        source=path.read_text(encoding="utf-8")
        tree=ast.parse(source, filename=rel)
    except Exception as exc:
        findings.append((rel,0,"PARSE_ERROR",str(exc),True))
        continue

    is_test=(
        rel.startswith("tests/")
        or rel.startswith("tools/")
        or rel.startswith("eval/")
        or rel.startswith("apply_patch_")
        or rel.endswith("_PATCH.md")
        or "PATCH_" in rel
    )

    for node in ast.walk(tree):
        if isinstance(node,ast.Call):
            name=""
            if isinstance(node.func,ast.Name):
                name=node.func.id
            elif isinstance(node.func,ast.Attribute):
                name=node.func.attr

            if name=="ActionRequest":
                bad=(not is_test and rel not in ALLOW_ACTIONREQUEST)
                findings.append((rel,node.lineno,"ActionRequest",name,bad))

            if name=="add_action_request":
                bad=(not is_test and rel not in ALLOW_ADD_ACTION)
                findings.append((rel,node.lineno,"add_action_request",name,bad))

            if name in {"execute","execute_resolved"} and isinstance(node.func,ast.Attribute):
                owner=""
                if isinstance(node.func.value,ast.Name):
                    owner=node.func.value.id
                token=f"{owner}.{name}"
                if "adapter" in owner.lower() or rel.startswith("stillpoint/adapters/"):
                    bad=(not is_test and rel not in ALLOW_ADAPTER_EXECUTION)
                    findings.append((rel,node.lineno,"adapter_execute",token,bad))

        if isinstance(node,ast.Constant) and isinstance(node.value,str):
            upper=node.value.upper()
            if "ACTION_REQUESTS" in upper and (
                "INSERT" in upper or "UPDATE" in upper or "DELETE" in upper
            ):
                bad=(not is_test and rel not in ALLOW_ACTION_SQL)
                findings.append((rel,getattr(node,"lineno",0),"action_sql","SQL",bad))

bad=[item for item in findings if item[-1]]
for rel,line,kind,detail,is_bad in findings:
    marker="FAIL" if is_bad else "OK"
    print(f"{marker} {rel}:{line} {kind} {detail}")

if bad:
    print(f"\n{len(bad)} production bypass candidate(s) found.")
    raise SystemExit(1)

print("\nAction boundary audit passed.")
