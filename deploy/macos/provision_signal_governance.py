#!/usr/bin/env python3
from __future__ import annotations
import json, os
from pathlib import Path

from stillpoint.db import CompanyDB
from stillpoint.signal_mail_governance_policy import (
    SignalMailGovernanceProvisioner,
    build_bootstrap_plan,
)

APPROVED = "abbada7549a95510d9552441a4f7bb1c92977f899cdfa953e8e394b058d00cc9"

def main() -> int:
    root = Path(os.environ["STILLPOINT_ROOT"]).expanduser().resolve()
    source = Path(os.environ["STILLPOINT_SOURCE_ROOT"]).expanduser().resolve()
    draft_path = source / "tests" / "fixtures" / "signal_icloud_personal_business.draft.json"
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    plan = build_bootstrap_plan(draft)
    if plan.governance_sha256 != APPROVED:
        raise SystemExit(
            f"governance digest mismatch: expected {APPROVED}, got {plan.governance_sha256}"
        )
    state = root / "state"
    state.mkdir(parents=True, exist_ok=True)
    facts = state / "signal_icloud_personal_business.facts.json"
    with CompanyDB(state / "company.sqlite") as db:
        provisioner = SignalMailGovernanceProvisioner(db)
        seeded = provisioner.seed(
            draft,
            expected_draft_sha256=plan.draft_sha256,
            ceo_confirmed=True,
        )
        applied = provisioner.apply(
            plan.governance_spec,
            facts_file=facts,
            expected_sha256=APPROVED,
            ceo_confirmed=True,
        )
    print(json.dumps({
        "governance_sha256": APPROVED,
        "delegation_id": applied["delegation_id"],
        "trigger_id": applied["trigger_id"],
        "mailbox": applied["mailbox"],
        "facts_file": str(facts),
        "seeded": bool(seeded.get("seeded")),
        "applied": bool(applied.get("applied")),
        "reused_existing": bool(applied.get("reused_existing")),
        "external_action": False,
    }, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
