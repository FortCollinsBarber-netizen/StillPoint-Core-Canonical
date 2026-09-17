#!/usr/bin/env python3
"""Strict isolated SQLite lifecycle audit for the production Signal host.

This audit intentionally does NOT run the historical test suite. It exercises
the production-owned lifecycle in a fresh interpreter:

1. create and migrate the canonical CompanyDB;
2. provision the exact approved Apple-first Signal governance;
3. run provider-neutral readiness using its read-only DB lifecycle;
4. assemble the live mailbox service with the mock model provider (no network
   operation is invoked);
5. close the production assembly;
6. force garbage collection with ResourceWarning promoted to an exception;
7. fail if any unclosed sqlite3.Connection is observed through unraisablehook.

Historical test-fixture cleanup is a separate maintenance concern. This audit
answers the production question: do the DB handles owned by the deployed
Signal lifecycle close when the lifecycle is used correctly?
"""
from __future__ import annotations

import gc
import json
import sys
import tempfile
import warnings
from pathlib import Path

from stillpoint.db import CompanyDB
from stillpoint.signal_mail_governance_policy import (
    SignalMailGovernanceProvisioner,
    build_bootstrap_plan,
)
from stillpoint.signal_mail_service import (
    SignalMailboxServiceConfig,
    build_signal_mailbox_service,
    readiness,
)

APPROVED = "abbada7549a95510d9552441a4f7bb1c92977f899cdfa953e8e394b058d00cc9"
ACCOUNT = "fortcollinsbarber@icloud.com"
JURISDICTION = "personal_business"
DELEGATION = "signal-delegation-icloud-personal-business-v1"
TRIGGER = "signal-trigger-icloud-personal-business-v1"


class UnraisableCapture:
    def __init__(self):
        self.items = []

    def __call__(self, args):
        self.items.append(
            {
                "exc_type": getattr(args.exc_type, "__name__", str(args.exc_type)),
                "exc_value": str(args.exc_value),
                "object": repr(args.object),
                "err_msg": str(args.err_msg or ""),
            }
        )


def main() -> int:
    capture = UnraisableCapture()
    old_hook = sys.unraisablehook
    sys.unraisablehook = capture
    warnings.simplefilter("error", ResourceWarning)

    try:
        with tempfile.TemporaryDirectory(prefix="stillpoint-prod-lifecycle-") as td:
            root = Path(td)
            source = Path(__file__).resolve().parents[1]
            draft_path = source / "tests" / "fixtures" / "signal_icloud_personal_business.draft.json"
            draft = json.loads(draft_path.read_text(encoding="utf-8"))
            plan = build_bootstrap_plan(draft)
            if plan.governance_sha256 != APPROVED:
                raise RuntimeError(
                    f"governance digest mismatch: expected {APPROVED}, got {plan.governance_sha256}"
                )

            state = root / "state"
            facts = state / "signal_icloud_personal_business.facts.json"
            with CompanyDB(state / "company.sqlite") as db:
                provisioner = SignalMailGovernanceProvisioner(db)
                provisioner.seed(
                    draft,
                    expected_draft_sha256=plan.draft_sha256,
                    ceo_confirmed=True,
                )
                provisioner.apply(
                    plan.governance_spec,
                    facts_file=facts,
                    expected_sha256=APPROVED,
                    ceo_confirmed=True,
                )

            env = {
                "STILLPOINT_ROOT": str(root),
                "STILLPOINT_MAIL_PROVIDER": "icloud",
                "STILLPOINT_MAIL_ACCOUNT": ACCOUNT,
                "STILLPOINT_MAIL_JURISDICTION": JURISDICTION,
                "STILLPOINT_ICLOUD_APP_PASSWORD": "lifecycle-audit-placeholder",
                "STILLPOINT_SIGNAL_DELEGATION_ID": DELEGATION,
                "STILLPOINT_SIGNAL_MAIL_TRIGGER_ID": TRIGGER,
                "STILLPOINT_SIGNAL_GOVERNANCE_SHA256": APPROVED,
                "STILLPOINT_SIGNAL_FACTS_FILE": str(facts),
                "STILLPOINT_PROVIDER": "mock",
                "STILLPOINT_SIGNAL_ALLOW_MOCK": "1",
                "STILLPOINT_SIGNAL_MODEL": "default",
            }
            config = SignalMailboxServiceConfig.from_env(env)

            result = readiness(config)
            if not result.get("ready"):
                raise RuntimeError(f"production readiness failed in lifecycle audit: {result}")

            assembly = build_signal_mailbox_service(config)
            assembly.close()
            del assembly
            del config
            del result

            # Multiple collections make cyclic fixture ownership deterministic.
            for _ in range(4):
                gc.collect()

        for _ in range(4):
            gc.collect()

    finally:
        sys.unraisablehook = old_hook

    sqlite_leaks = [
        item for item in capture.items
        if item["exc_type"] == "ResourceWarning"
        and "unclosed database" in item["exc_value"].lower()
    ]
    if sqlite_leaks:
        print(json.dumps({"ok": False, "sqlite_resource_leaks": sqlite_leaks}, indent=2))
        return 1

    if capture.items:
        print(json.dumps({"ok": False, "unexpected_unraisable": capture.items}, indent=2))
        return 1

    print(json.dumps({
        "ok": True,
        "audit": "production_sqlite_resource_lifecycle",
        "mailbox": {
            "provider": "icloud",
            "account": ACCOUNT,
            "jurisdiction": JURISDICTION,
        },
        "governance_sha256": APPROVED,
        "network_actions_invoked": False,
        "sqlite_resource_leaks": 0,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
