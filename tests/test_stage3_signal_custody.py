from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from stillpoint.db import CompanyDB
from stillpoint.mail_contracts import MailboxIdentity
from stillpoint.signal_mail_service import (
    SignalMailboxServiceConfig,
    SignalServiceConfigurationError,
    _record_signal_health,
    _require_materialized_facts,
)


class Stage3SignalCustodyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.db=CompanyDB(self.root/"company.sqlite")
        self.facts=self.root/"facts.json"
        self.facts.write_text('{"facts":"current"}\n',encoding="utf-8")
        self.digest="a"*64
        self.config=SignalMailboxServiceConfig(
            root=self.root,
            model_provider="mock",
            model="mock",
            identity=MailboxIdentity("icloud","owner@icloud.com","personal"),
            credential="mail-secret",
            delegation_id="delegation-1",
            trigger_id="trigger-1",
            governance_sha256=self.digest,
            facts_file=self.facts,
            worker_id="signal-worker-1",
            allow_mock_provider=True,
        )

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def _record(self,status="materialized"):
        now="2026-09-18T18:45:00+00:00"
        sha=hashlib.sha256(self.facts.read_bytes()).hexdigest()
        self.db.conn.execute(
            """INSERT INTO signal_governance_materializations(
               governance_sha256,facts_path,delegation_id,trigger_id,facts_sha256,
               status,last_error,created_at,updated_at,materialized_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                self.digest,str(self.facts),"delegation-1","trigger-1",sha,
                status,None,now,now,now if status=="materialized" else None,
            ),
        )
        self.db.conn.commit()
        return sha

    def test_exact_materialized_facts_pass(self):
        expected=self._record()
        row=_require_materialized_facts(self.db,self.config)
        self.assertEqual(row["status"],"materialized")
        self.assertEqual(row["facts_sha256"],expected)

    def test_mutated_facts_fail_closed(self):
        self._record()
        self.facts.write_text('{"facts":"changed"}\n',encoding="utf-8")
        with self.assertRaisesRegex(
            SignalServiceConfigurationError,
            "digest does not match",
        ):
            _require_materialized_facts(self.db,self.config)

    def test_pending_materialization_is_not_operational(self):
        self._record(status="pending")
        with self.assertRaisesRegex(
            SignalServiceConfigurationError,
            "not materialized: pending",
        ):
            _require_materialized_facts(self.db,self.config)

    def test_health_transition_is_durable(self):
        _record_signal_health(
            self.db,
            self.config,
            status="degraded",
            error="mailbox unavailable",
            detail={"source":"test"},
            occurred_at="2026-09-18T18:46:00+00:00",
        )
        row=self.db.conn.execute(
            "SELECT * FROM signal_service_health_events ORDER BY occurred_at DESC LIMIT 1"
        ).fetchone()
        self.assertEqual(row["status"],"degraded")
        self.assertEqual(row["worker_id"],"signal-worker-1")
        self.assertEqual(row["error"],"mailbox unavailable")


if __name__=="__main__":
    unittest.main()
