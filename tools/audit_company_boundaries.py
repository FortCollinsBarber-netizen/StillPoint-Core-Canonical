#!/usr/bin/env python3
"""Audit specialist/company boundaries against the earned StillPoint architecture."""

from __future__ import annotations

import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path.cwd()

EXPECTED={
    "orchestra","author","press","signal","ledger","research","builder","stillpoint"
}

errors=[]

canonical=ROOT/"config"/"agents.json"
packaged=ROOT/"stillpoint"/"defaults"/"agents.json"
if not canonical.is_file():
    errors.append("config/agents.json missing")
else:
    raw=json.loads(canonical.read_text(encoding="utf-8"))
    agents=raw.get("agents") or []
    ids=[a.get("id") for a in agents]
    if set(ids)!=EXPECTED or len(ids)!=len(EXPECTED):
        errors.append(f"agent ids mismatch: {ids}")
    for agent in agents:
        aid=agent.get("id")
        if not agent.get("does_not_own"):
            errors.append(f"{aid}: does_not_own must not be empty")
        if agent.get("tools"):
            errors.append(
                f"{aid}: durable registry tools must remain empty; capabilities are request-scoped"
            )

if canonical.is_file() and packaged.is_file():
    if canonical.read_bytes()!=packaged.read_bytes():
        errors.append("packaged agent registry mirror differs from canonical registry")
else:
    errors.append("packaged agent registry mirror missing")

# Dynamic capability matrix: the strongest plausible plan request must still be
# reduced to the role's bounded request-scoped capabilities.
try:
    from stillpoint.capabilities import capabilities_for_call
    caps=["web_research","x_research","code_execution","structured_output"]
    cases={
        "orchestra": set(),
        "author": set(),
        "press": {"web_research"},
        "signal": {"web_research","x_research"},
        "ledger": {"web_research","code_execution"},
        "research": {"web_research","x_research"},
        "builder": {"web_research","code_execution"},
    }
    for aid,expected in cases.items():
        got={
            item.capability
            for item in capabilities_for_call(
                agent_id=aid,
                plan_capabilities=list(caps),
                agent_capabilities=list(caps),
                review_reason="",
                scoped_requests=None,
            )
        }
        if got!=expected:
            errors.append(f"{aid}: capability boundary {got} != {expected}")

    # Still Point receives no default tools merely because it is the reviewer.
    got={
        item.capability
        for item in capabilities_for_call(
            agent_id="stillpoint",
            plan_capabilities=list(caps),
            agent_capabilities=list(caps),
            review_reason="ordinary integrity review",
            scoped_requests=None,
        )
    }
    if got:
        errors.append(f"stillpoint: ordinary review unexpectedly owns tools {got}")
except Exception as exc:
    errors.append(f"capability audit failed: {type(exc).__name__}: {exc}")

# Prompt-level constitutional guardrails must stay explicit.
try:
    from stillpoint.prompts import COMMON
    required=[
        "human CEO and final authority",
        "require explicit CEO authorization",
        "untrusted data, not instructions",
    ]
    for token in required:
        if token not in COMMON:
            errors.append(f"COMMON prompt missing guardrail: {token!r}")
except Exception as exc:
    errors.append(f"prompt audit failed: {type(exc).__name__}: {exc}")

if errors:
    for item in errors:
        print("FAIL",item)
    raise SystemExit(1)

print("Company boundary audit passed.")
