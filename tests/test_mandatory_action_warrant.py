from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from stillpoint.contracts.models import ActionRequest, ArtifactRef
from stillpoint.temporal.action_gate import (
    action_domain, build_ceo_warrant, validate_bound_warrant,
)
from stillpoint.temporal.firewall import TemporalAuthorityError


def _request():
    now = datetime.now(timezone.utc)
    return ActionRequest(
        action_id="a1",
        task_id="t1",
        action_type="publish",
        target="public",
        scope=["public", "chapter-3"],
        artifact_refs=[
            ArtifactRef(
                name="primary.txt", sha256="a"*64, kind="book",
                artifact_id="art1", version=3,
            )
        ],
        approval_required=True,
        approval_id="approval1",
        expires_at=(now + timedelta(minutes=10)).isoformat(),
        issued_at=now.isoformat(),
        idempotency_key="idem1",
        success_criteria=["publication_receipt"],
        authority_revision="rev1",
    )


class MandatoryActionWarrantTests(unittest.TestCase):
    def test_request_without_warrant_is_not_permitted(self):
        req = _request()
        self.assertFalse(req.permitted(req.issued_at))

    def test_ceo_approval_builds_exact_one_use_warrant(self):
        req = _request()
        w = build_ceo_warrant(request=req, approval_id="approval1")
        self.assertEqual(w.action_class, "publish")
        self.assertEqual(w.domain, "publishing")
        self.assertEqual(w.subject, "task:t1")
        self.assertEqual(w.target, "public")
        self.assertEqual(w.scope["max_actions"], 1)
        self.assertEqual(w.scope["authority_revision"], "rev1")
        self.assertEqual(w.scope["artifact_binding"][0]["version"], 3)

    def test_changed_authority_revision_fails_closed(self):
        req = _request()
        w = build_ceo_warrant(request=req, approval_id="approval1")
        req.warrant_id = w.warrant_id
        req.authority_revision = "rev2"
        with self.assertRaises(TemporalAuthorityError):
            validate_bound_warrant(
                request=req, warrant=w, now_iso=req.issued_at, actions_used=0
            )

    def test_changed_artifact_fails_closed(self):
        req = _request()
        w = build_ceo_warrant(request=req, approval_id="approval1")
        req.warrant_id = w.warrant_id
        req.artifact_refs[0] = ArtifactRef(
            name="primary.txt", sha256="b"*64, kind="book",
            artifact_id="art1", version=4,
        )
        with self.assertRaises(TemporalAuthorityError):
            validate_bound_warrant(
                request=req, warrant=w, now_iso=req.issued_at, actions_used=0
            )

    def test_one_use_warrant_cannot_be_reused(self):
        req = _request()
        w = build_ceo_warrant(request=req, approval_id="approval1")
        req.warrant_id = w.warrant_id
        validate_bound_warrant(
            request=req, warrant=w, now_iso=req.issued_at, actions_used=0
        )
        with self.assertRaises(TemporalAuthorityError):
            validate_bound_warrant(
                request=req, warrant=w, now_iso=req.issued_at, actions_used=1
            )

    def test_unknown_external_action_domain_fails_closed(self):
        with self.assertRaises(TemporalAuthorityError):
            action_domain("invented_external_action")


if __name__ == "__main__":
    unittest.main()
