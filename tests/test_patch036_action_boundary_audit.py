from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

AUDIT = Path(__file__).resolve().parents[1] / "tools" / "audit_action_request_boundaries.py"


def run_audit(files: dict[str, str]):
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        for rel, text in files.items():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        return subprocess.run(
            [sys.executable, str(AUDIT), str(root)],
            text=True,
            capture_output=True,
        )


class Patch036ActionBoundaryAuditTests(unittest.TestCase):
    def test_sqlite_execute_inside_adapter_file_is_not_external_adapter_execution(self):
        r = run_audit({
            "stillpoint/adapters/gmail_inbox.py":
                "def poll(c):\n"
                "    c.execute('UPDATE signal_gmail_mailboxes SET status=?',('x',))\n"
        })
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_actual_adapter_execute_outside_earned_boundary_fails(self):
        r = run_audit({
            "stillpoint/rogue.py":
                "def x(adapter):\n"
                "    return adapter.execute('boom')\n"
        })
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("production bypass candidate", r.stdout)

    def test_signal_preparation_exact_non_authorizing_shape_passes(self):
        r = run_audit({
            "stillpoint/signal_email.py":
                "def execute(self):\n"
                "    req=ActionRequest(action_id='a',task_id='t',action_type='send_email',"
                "target='x',scope=[],artifact_refs=[],approval_required=True,approval_id=None,"
                "expires_at='x',issued_at='x',idempotency_key='k',"
                "success_criteria=['provider_acceptance_receipt'])\n"
                "    self.db.add_action_request(req)\n"
        })
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_signal_preparation_with_prebound_warrant_fails(self):
        r = run_audit({
            "stillpoint/signal_email.py":
                "def execute(self):\n"
                "    req=ActionRequest(action_id='a',task_id='t',action_type='send_email',"
                "target='x',scope=[],artifact_refs=[],approval_required=True,approval_id=None,"
                "expires_at='x',issued_at='x',idempotency_key='k',"
                "success_criteria=['provider_acceptance_receipt'],warrant_id='already')\n"
                "    self.db.add_action_request(req)\n"
        })
        self.assertNotEqual(r.returncode, 0)

    def test_delegated_warrant_sql_only_exact_issuer_method_passes(self):
        r = run_audit({
            "stillpoint/authority/delegated_warrants.py":
                "class DelegatedWarrantIssuer:\n"
                "    def authorize_waiting_action(self,conn):\n"
                "        conn.execute(\"UPDATE action_requests SET warrant_id=? WHERE id=?\",('w','a'))\n"
        })
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_action_sql_in_other_delegated_function_fails(self):
        r = run_audit({
            "stillpoint/authority/delegated_warrants.py":
                "def unsafe(conn):\n"
                "    conn.execute(\"UPDATE action_requests SET warrant_id=? WHERE id=?\",('w','a'))\n"
        })
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
