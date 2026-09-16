#!/usr/bin/env python3
"""Source-tree release gate that composes StillPoint's deterministic audits."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path.cwd()

commands=[
    [sys.executable, str(ROOT/"tools"/"audit_action_request_boundaries.py"), str(ROOT)],
    [sys.executable, str(ROOT/"tools"/"audit_company_boundaries.py"), str(ROOT)],
]

for command in commands:
    print("+"," ".join(command))
    completed=subprocess.run(command,cwd=ROOT)
    if completed.returncode:
        raise SystemExit(completed.returncode)

from eval.frozen import verify_frozen_corpora
verified=verify_frozen_corpora()
print("Frozen evaluator integrity:",verified)

print("Static release audits passed.")
