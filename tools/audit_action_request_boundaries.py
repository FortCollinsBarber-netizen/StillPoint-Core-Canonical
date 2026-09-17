#!/usr/bin/env python3
"""Repository-wide audit for consequential action bypasses.

This audit distinguishes four boundaries:
- ActionRequest construction
- durable action-request persistence
- external adapter execution
- direct SQL mutation of action_requests

It is deliberately fail-closed, but function-scoped for earned production
boundaries. Ordinary SQLite .execute() calls inside an adapter module are not
external adapter execution merely because of their file location.
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()

WILDCARD = "*"

ALLOW_ACTIONREQUEST = {
    ("stillpoint/runtime.py", WILDCARD),
}
ALLOW_ADD_ACTION = {
    ("stillpoint/runtime.py", WILDCARD),
}
ALLOW_ADAPTER_EXECUTION = {
    ("stillpoint/runtime.py", WILDCARD),
    ("stillpoint/adapters/registry.py", WILDCARD),
}
ALLOW_ACTION_SQL = {
    ("stillpoint/db.py", WILDCARD),
    ("stillpoint/runtime.py", WILDCARD),  # re-entry metadata binding only
    # This exact issuer method performs the atomic transition from a waiting
    # request to a one-use delegated warrant after all standing checks pass.
    ("stillpoint/authority/delegated_warrants.py", "authorize_waiting_action"),
}

SIGNAL_PREP_PATH = "stillpoint/signal_email.py"
SIGNAL_PREP_FUNCTION = "execute"

findings = []


def _is_test_path(rel: str) -> bool:
    return (
        rel.startswith("tests/")
        or rel.startswith("tools/")
        or rel.startswith("eval/")
        or rel.startswith("apply_patch_")
        or rel.endswith("_PATCH.md")
        or "PATCH_" in rel
    )


def _parents(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    out: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            out[child] = parent
    return out


def _enclosing_function(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> ast.AST | None:
    cur = node
    while cur in parents:
        cur = parents[cur]
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return cur
    return None


def _fn_name(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> str:
    fn = _enclosing_function(node, parents)
    return fn.name if fn is not None else ""


def _allowed(rel: str, fn: str, rules: set[tuple[str, str]]) -> bool:
    return (rel, fn) in rules or (rel, WILDCARD) in rules


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def _owner_expr(node: ast.Call) -> str:
    if not isinstance(node.func, ast.Attribute):
        return ""
    try:
        return ast.unparse(node.func.value)
    except Exception:
        return ""


def _kw(call: ast.Call, name: str):
    for item in call.keywords:
        if item.arg == name:
            return item.value
    return None


def _const(node):
    return node.value if isinstance(node, ast.Constant) else object()


def _safe_signal_request_constructor(call: ast.Call, rel: str, fn: str) -> bool:
    """Allow only a non-authorizing prepared email request in Signal.

    The constructor must prove at audit time that:
    - action type is exactly send_email;
    - explicit human approval is initially required;
    - no approval is already bound;
    - no warrant is already bound;
    - success evidence is provider acceptance only.

    Standing-delegation authorization happens later in the dedicated warrant
    issuer after a fresh action-specific evaluation.
    """
    if rel != SIGNAL_PREP_PATH or fn != SIGNAL_PREP_FUNCTION:
        return False

    action_type = _kw(call, "action_type")
    approval_required = _kw(call, "approval_required")
    approval_id = _kw(call, "approval_id")
    warrant_id = _kw(call, "warrant_id")
    success = _kw(call, "success_criteria")

    if _const(action_type) != "send_email":
        return False
    if _const(approval_required) is not True:
        return False
    if not isinstance(approval_id, ast.Constant) or approval_id.value is not None:
        return False
    if warrant_id is not None and (not isinstance(warrant_id, ast.Constant) or warrant_id.value is not None):
        return False
    if not isinstance(success, (ast.List, ast.Tuple)):
        return False
    values = [_const(x) for x in success.elts]
    if values != ["provider_acceptance_receipt"]:
        return False
    return True


def _function_has_safe_signal_req_binding(
    fn_node: ast.AST | None, rel: str, fn: str, variable: str
) -> bool:
    if fn_node is None or rel != SIGNAL_PREP_PATH or fn != SIGNAL_PREP_FUNCTION:
        return False
    for item in ast.walk(fn_node):
        if not isinstance(item, (ast.Assign, ast.AnnAssign)):
            continue
        value = item.value
        targets = item.targets if isinstance(item, ast.Assign) else [item.target]
        if not isinstance(value, ast.Call) or _call_name(value) != "ActionRequest":
            continue
        bound = any(isinstance(t, ast.Name) and t.id == variable for t in targets)
        if bound and _safe_signal_request_constructor(value, rel, fn):
            return True
    return False


for path in sorted(ROOT.rglob("*.py")):
    rel = path.relative_to(ROOT).as_posix()
    if any(part in {".git", ".venv", "venv", "__pycache__", "build", "dist"} for part in path.parts):
        continue
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=rel)
    except Exception as exc:
        findings.append((rel, 0, "PARSE_ERROR", str(exc), True))
        continue

    is_test = _is_test_path(rel)
    parents = _parents(tree)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = _call_name(node)
            fn_node = _enclosing_function(node, parents)
            fn = fn_node.name if fn_node is not None else ""

            if name == "ActionRequest":
                safe_signal = _safe_signal_request_constructor(node, rel, fn)
                bad = not is_test and not _allowed(rel, fn, ALLOW_ACTIONREQUEST) and not safe_signal
                detail = "prepared_signal_request" if safe_signal else name
                findings.append((rel, node.lineno, "ActionRequest", detail, bad))

            if name == "add_action_request":
                safe_signal_add = False
                if rel == SIGNAL_PREP_PATH and fn == SIGNAL_PREP_FUNCTION and node.args:
                    arg = node.args[0]
                    if isinstance(arg, ast.Name):
                        safe_signal_add = _function_has_safe_signal_req_binding(
                            fn_node, rel, fn, arg.id
                        )
                bad = not is_test and not _allowed(rel, fn, ALLOW_ADD_ACTION) and not safe_signal_add
                detail = "prepared_signal_request" if safe_signal_add else name
                findings.append((rel, node.lineno, "add_action_request", detail, bad))

            if name in {"execute", "execute_resolved"} and isinstance(node.func, ast.Attribute):
                owner = _owner_expr(node)
                # Only adapter-like receivers count. This avoids treating
                # sqlite3 Connection.execute() as an external action merely
                # because it happens inside stillpoint/adapters/.
                adapter_like = "adapter" in owner.lower()
                registry_internal = (
                    rel == "stillpoint/adapters/registry.py"
                    and owner in {"self", "adapter", "selected_adapter"}
                )
                if adapter_like or registry_internal:
                    bad = not is_test and not _allowed(rel, fn, ALLOW_ADAPTER_EXECUTION)
                    findings.append((rel, node.lineno, "adapter_execute", f"{owner}.{name}", bad))

        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            upper = node.value.upper()
            if "ACTION_REQUESTS" in upper and (
                "INSERT" in upper or "UPDATE" in upper or "DELETE" in upper
            ):
                fn = _fn_name(node, parents)
                bad = not is_test and not _allowed(rel, fn, ALLOW_ACTION_SQL)
                findings.append((rel, getattr(node, "lineno", 0), "action_sql", f"SQL@{fn or '<module>'}", bad))

bad = [item for item in findings if item[-1]]
for rel, line, kind, detail, is_bad in findings:
    marker = "FAIL" if is_bad else "OK"
    print(f"{marker} {rel}:{line} {kind} {detail}")

if bad:
    print(f"\n{len(bad)} production bypass candidate(s) found.")
    raise SystemExit(1)

print("\nAction boundary audit passed.")
