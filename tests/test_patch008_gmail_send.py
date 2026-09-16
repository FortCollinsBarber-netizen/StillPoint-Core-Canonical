from __future__ import annotations

import base64
import hashlib
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from email import policy
from email.parser import BytesParser
from pathlib import Path
from unittest.mock import patch

from stillpoint.adapters.gmail_send import (
    GmailSendAdapter,
    GmailSendBoundaryError,
    parse_authorized_send_target,
)
from stillpoint.adapters.outbox import BoundedOutboxAdapter, OutboxBoundaryError, _atomic_write
from stillpoint.adapters.production import configured_outbox_root, inspect_production_adapters
from stillpoint.contracts.models import ActionRequest, ArtifactRef


class FakeDB:
    def __init__(self, body="PATCH008 EMAIL BODY"):
        self.body=body
        self.digest=hashlib.sha256(body.encode("utf-8")).hexdigest()

    def get_artifact(self, artifact_id):
        return {
            "id":artifact_id,
            "task_id":"task-1",
            "version":1,
            "sha256":self.digest,
            "produced_by_run_id":"run-1",
        }

    def get_run(self, run_id):
        return {"id":run_id,"output":self.body}


class FakeResponse:
    def __init__(self,data): self.data=data
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self): return self.data


class FakeGmail:
    def __init__(self):
        self.calls=[]
        self.fail=None
        self.sent=[]
        self.invalid_send_response=False

    @staticmethod
    def _decode(raw):
        raw=raw+"="*((4-len(raw)%4)%4)
        return base64.urlsafe_b64decode(raw.encode("ascii"))

    def __call__(self, request, timeout=None):
        self.calls.append((request,timeout))
        if self.fail:
            raise self.fail
        method=request.get_method()
        url=request.full_url
        if method=="POST" and url.endswith("/messages/send"):
            payload=json.loads(request.data.decode("utf-8"))
            mime=self._decode(payload["raw"])
            msg=BytesParser(policy=policy.default).parsebytes(mime)
            item={
                "id":f"msg-{len(self.sent)+1}",
                "threadId":"thread-1",
                "mime":mime,
                "message-id":msg["Message-ID"],
                "from":msg["From"],
                "to":msg["To"],
                "subject":msg["Subject"],
            }
            self.sent.append(item)
            if self.invalid_send_response:
                return FakeResponse(b"{bad-json")
            return FakeResponse(json.dumps({"id":item["id"],"threadId":item["threadId"]}).encode("utf-8"))
        if method=="GET" and "/messages?" in url:
            parsed=__import__("urllib.parse").parse.urlparse(url)
            q=__import__("urllib.parse").parse.parse_qs(parsed.query).get("q",[""])[0]
            marker=q.split(" in:sent",1)[0].removeprefix("rfc822msgid:")
            matches=[{"id":m["id"],"threadId":m["threadId"]} for m in self.sent if m["message-id"]==marker]
            return FakeResponse(json.dumps({"messages":matches,"resultSizeEstimate":len(matches)}).encode("utf-8"))
        if method=="GET" and "/messages/" in url:
            message_id=url.split("/messages/",1)[1].split("?",1)[0]
            item=next(m for m in self.sent if m["id"]==message_id)
            headers=[
                {"name":"Message-ID","value":item["message-id"]},
                {"name":"From","value":item["from"]},
                {"name":"To","value":item["to"]},
                {"name":"Subject","value":item["subject"]},
            ]
            return FakeResponse(json.dumps({"id":item["id"],"threadId":item["threadId"],"payload":{"headers":headers}}).encode("utf-8"))
        raise AssertionError(f"unexpected Gmail request {method} {url}")


def request_for(db):
    now=datetime.now(timezone.utc)
    return ActionRequest(
        action_id="action-1",
        task_id="task-1",
        action_type="send_email",
        target="Send an email from operator@example.com to recipient@example.com subject: Project update",
        scope=[
            "external_person",
            "Send an email from operator@example.com to recipient@example.com subject: Project update",
        ],
        artifact_refs=[ArtifactRef(
            name="primary.txt",
            sha256=db.digest,
            kind="communication_draft",
            artifact_id="artifact-1",
            version=1,
        )],
        approval_required=True,
        approval_id="approval-1",
        expires_at=(now+timedelta(hours=1)).isoformat(),
        issued_at=now.isoformat(),
        idempotency_key="idem-1",
        success_criteria=["delivery_receipt"],
        authority_revision="rev-1",
        warrant_id="warrant-1",
    )


class Patch008GmailSendTests(unittest.TestCase):
    def test_target_parser_binds_sender_recipient_subject(self):
        self.assertEqual(
            parse_authorized_send_target(
                "Send an email from operator@example.com to recipient@example.com subject: Project update"
            ),
            ("operator@example.com","recipient@example.com","Project update"),
        )

    def test_target_parser_rejects_missing_sender_multiple_recipient_and_cc(self):
        bad=[
            "Send an email to recipient@example.com subject: Project update",
            "Send an email from operator@example.com to one@example.com and two@example.com subject: Project update",
            "Send an email from operator@example.com to recipient@example.com cc: other@example.com subject: Project update",
        ]
        for text in bad:
            with self.subTest(text=text):
                with self.assertRaises(GmailSendBoundaryError):
                    parse_authorized_send_target(text)

    def test_adapter_posts_one_plain_text_message_to_send_endpoint(self):
        db=FakeDB();fake=FakeGmail();req=request_for(db)
        adapter=GmailSendAdapter(
            db=db,account="operator@example.com",access_token="secret",enabled=True,urlopen=fake
        )
        result=adapter.execute(req)
        self.assertEqual(result.status,"succeeded")
        self.assertEqual(result.external_id,"msg-1")
        self.assertEqual(result.evidence[0].type,"delivery_receipt")
        self.assertEqual(result.evidence[0].satisfies,"delivery_receipt")
        self.assertEqual(len(fake.calls),1)
        http,_=fake.calls[0]
        self.assertEqual(http.get_method(),"POST")
        self.assertTrue(http.full_url.endswith("/users/operator%40example.com/messages/send"))
        self.assertNotIn("secret",json.dumps(json.loads(result.evidence[0].note)))
        msg=BytesParser(policy=policy.default).parsebytes(fake.sent[0]["mime"])
        self.assertEqual(msg["From"],"operator@example.com")
        self.assertEqual(msg["To"],"recipient@example.com")
        self.assertEqual(msg["Subject"],"Project update")
        self.assertEqual(len(list(msg.iter_attachments())),0)
        self.assertIn("PATCH008 EMAIL BODY",msg.get_body(preferencelist=("plain",)).get_content())

    def test_configured_account_change_cannot_redirect_authorized_send(self):
        db=FakeDB();req=request_for(db)
        wrong=GmailSendAdapter(
            db=db,account="different@example.com",access_token="secret",enabled=True,urlopen=FakeGmail()
        )
        self.assertFalse(wrong.can_execute(req))
        with self.assertRaises(GmailSendBoundaryError):
            wrong.execute(req)

    def test_timeout_is_single_attempt_no_adapter_retry(self):
        db=FakeDB();fake=FakeGmail();fake.fail=TimeoutError("simulated")
        adapter=GmailSendAdapter(
            db=db,account="operator@example.com",access_token="secret",enabled=True,urlopen=fake
        )
        with self.assertRaises(GmailSendBoundaryError):
            adapter.execute(request_for(db))
        self.assertEqual(len(fake.calls),1)

    def test_uncertain_post_effect_can_be_confirmed_by_exact_sent_message(self):
        db=FakeDB();fake=FakeGmail();fake.invalid_send_response=True
        adapter=GmailSendAdapter(
            db=db,account="operator@example.com",access_token="secret",enabled=True,urlopen=fake
        )
        req=request_for(db)
        with self.assertRaises(GmailSendBoundaryError):
            adapter.execute(req)
        self.assertEqual(len(fake.sent),1)
        fake.invalid_send_response=False
        probe=adapter.probe_existing(req)
        self.assertIs(probe["effect_occurred"],True)
        self.assertEqual(probe["matches"],["msg-1"])

    def test_zero_reconciliation_matches_stays_ambiguous(self):
        db=FakeDB();adapter=GmailSendAdapter(
            db=db,account="operator@example.com",access_token="secret",enabled=True,urlopen=FakeGmail()
        )
        probe=adapter.probe_existing(request_for(db))
        self.assertIsNone(probe["effect_occurred"])

    def test_production_registry_is_default_off_and_does_not_echo_token(self):
        token="NEVER-ECHO-THIS"
        with patch.dict(os.environ,{
            "STILLPOINT_GMAIL_ACCOUNT":"operator@example.com",
            "STILLPOINT_GMAIL_ACCESS_TOKEN":token,
        },clear=True):
            status=inspect_production_adapters()
            self.assertEqual(status["enabled"],[])
            self.assertIn("gmail_send",status["available_disabled"])
            self.assertNotIn(token,json.dumps(status))

    def test_enablement_requires_account_and_token(self):
        with patch.dict(os.environ,{"STILLPOINT_ENABLE_GMAIL_SEND":"1"},clear=True):
            self.assertFalse(inspect_production_adapters()["ok"])

    def test_dangling_outbox_symlinks_are_rejected(self):
        if not hasattr(os,"symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d);target=tmp/"missing-target";link=tmp/"dangling"
            try:
                link.symlink_to(target,target_is_directory=True)
            except OSError:
                self.skipTest("symlink not permitted")
            self.assertTrue(link.is_symlink())
            self.assertFalse(link.exists())
            with patch.dict(os.environ,{"STILLPOINT_OUTBOX_ROOT":str(link)},clear=True):
                with self.assertRaises(Exception):
                    configured_outbox_root()
            with self.assertRaises(OutboxBoundaryError):
                BoundedOutboxAdapter(db=FakeDB(),outbox_root=link,enabled=True)

    def test_atomic_write_rejects_dangling_destination_symlink(self):
        if not hasattr(os,"symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d);dest=tmp/"dest";missing=tmp/"missing"
            try:
                dest.symlink_to(missing)
            except OSError:
                self.skipTest("symlink not permitted")
            with self.assertRaises(OutboxBoundaryError):
                _atomic_write(dest,b"data")

    def test_gmail_adapter_source_has_no_delete_update_draft_or_publish_endpoint(self):
        import stillpoint.adapters.gmail_send as module
        text=Path(module.__file__).read_text().lower()
        for forbidden in (
            "/drafts",
            'method="delete"',"method='delete'",
            'method="put"',"method='put'",
            'method="patch"',"method='patch'",
            "publish",
            "social_post",
        ):
            self.assertNotIn(forbidden,text)


if __name__=="__main__":
    unittest.main()
