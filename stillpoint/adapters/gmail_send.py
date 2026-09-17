from __future__ import annotations

import base64
import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from email.message import EmailMessage
from email.policy import SMTP
from email.utils import parseaddr

from ..contracts.models import ActionEvidence, ActionRequest, ActionResult


_SEND_ENDPOINT="https://gmail.googleapis.com/gmail/v1/users/{user_id}/messages/send"
_LIST_ENDPOINT="https://gmail.googleapis.com/gmail/v1/users/{user_id}/messages"
_GET_ENDPOINT="https://gmail.googleapis.com/gmail/v1/users/{user_id}/messages/{message_id}"
_EMAIL_RE=re.compile(r"^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$")
_FROM_RE=re.compile(r"\bfrom\s+<?([^\s,;<>]+@[^\s,;<>]+\.[^\s,;<>]+)>?",re.I)
_TO_RE=re.compile(r"\bto\s+<?([^\s,;<>]+@[^\s,;<>]+\.[^\s,;<>]+)>?",re.I)
_SUBJECT_RE=re.compile(r"\bsubject\s*:\s*(.+)\s*$",re.I|re.S)


class GmailSendBoundaryError(RuntimeError):
    pass


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _message_id(request: ActionRequest) -> str:
    return f"<stillpoint-{request.action_id}@stillpoint.invalid>"


def parse_authorized_send_target(text: str) -> tuple[str,str,str]:
    """Extract the exact sender, recipient, and subject already authorized in target.

    Patch 008 deliberately supports one plain-text message, one explicit sender account,
    and one explicit recipient. The CEO request must carry those values before approval.
    """
    target=(text or "").strip()
    lowered=target.lower()
    for forbidden in (" cc:"," bcc:","\ncc:","\nbcc:","reply to","forward ","attachment","attach "):
        if forbidden in lowered:
            raise GmailSendBoundaryError("Patch 008 does not authorize cc, bcc, replies, forwarding, or attachments")

    sender_match=_FROM_RE.search(target)
    recipient_match=_TO_RE.search(target)
    subject_match=_SUBJECT_RE.search(target)
    if not sender_match or not recipient_match or not subject_match:
        raise GmailSendBoundaryError(
            "send_email target must explicitly include 'from SENDER to RECIPIENT subject: SUBJECT' before approval"
        )

    sender=sender_match.group(1).strip().lower()
    recipient=recipient_match.group(1).strip().lower()
    subject=subject_match.group(1).strip()
    if not _EMAIL_RE.fullmatch(sender) or not _EMAIL_RE.fullmatch(recipient):
        raise GmailSendBoundaryError("invalid authorized sender or recipient address")
    if not subject or "\r" in subject or "\n" in subject:
        raise GmailSendBoundaryError("subject must be one non-empty header-safe line")
    if len(subject)>200:
        raise GmailSendBoundaryError("subject exceeds 200 characters")

    # Exactly two email-address occurrences are allowed: one From and one To.
    addresses=re.findall(r"[^\s,;<>]+@[^\s,;<>]+\.[^\s,;<>]+",target)
    if len(addresses)!=2:
        raise GmailSendBoundaryError("Patch 008 authorizes exactly one sender and one recipient")
    return sender,recipient,subject


def _headers(message: dict) -> dict[str,str]:
    payload=message.get("payload") if isinstance(message,dict) else None
    items=payload.get("headers") if isinstance(payload,dict) else None
    out={}
    for item in items or []:
        if not isinstance(item,dict):
            continue
        name=str(item.get("name") or "").strip().lower()
        if name and name not in out:
            out[name]=str(item.get("value") or "").strip()
    return out


class GmailSendAdapter:
    name="gmail_send"
    action_types=("send_email",)

    def __init__(self, *, db, account: str, access_token: str, enabled: bool=False, urlopen=None, timeout_seconds: int=30):
        self.db=db
        self.account=(account or "").strip().lower()
        self.access_token=(access_token or "").strip()
        self.enabled=bool(enabled)
        self._urlopen=urlopen or urllib.request.urlopen
        self.timeout_seconds=int(timeout_seconds)
        if not _EMAIL_RE.fullmatch(self.account):
            raise GmailSendBoundaryError("Gmail account must be an explicit email address")
        if self.enabled and not self.access_token:
            raise GmailSendBoundaryError("Gmail access token required when gmail_send is enabled")

    def _bound(self, request: ActionRequest):
        if request.action_type!="send_email":
            raise GmailSendBoundaryError("unsupported action type")
        if len(request.artifact_refs)!=1:
            raise GmailSendBoundaryError("Patch 008 Gmail send requires exactly one authorized artifact")
        sender,recipient,subject=parse_authorized_send_target(request.target)
        if sender!=self.account:
            raise GmailSendBoundaryError("configured Gmail account does not match the sender authorized before approval")
        if request.target not in request.scope:
            raise GmailSendBoundaryError("authorized send target is not present in ActionRequest scope")
        return sender,recipient,subject

    def _source(self, request: ActionRequest):
        ref=request.artifact_refs[0]
        if not ref.artifact_id:
            raise GmailSendBoundaryError("artifact id required")
        row=self.db.get_artifact(ref.artifact_id)
        if not row:
            raise GmailSendBoundaryError("artifact not found")
        if row["task_id"]!=request.task_id:
            raise GmailSendBoundaryError("artifact task mismatch")
        if int(row["version"])!=int(ref.version):
            raise GmailSendBoundaryError("artifact version mismatch")
        if row["sha256"]!=ref.sha256:
            raise GmailSendBoundaryError("artifact metadata hash mismatch")
        run=self.db.get_run(row["produced_by_run_id"])
        if not run:
            raise GmailSendBoundaryError("artifact source run not found")
        body=str(run["output"]).encode("utf-8")
        if _sha(body)!=ref.sha256:
            raise GmailSendBoundaryError("artifact content hash mismatch")
        return ref,body

    def can_execute(self, request: ActionRequest) -> bool:
        if not self.enabled or request.action_type not in self.action_types:
            return False
        try:
            self._bound(request)
            self._source(request)
        except Exception:
            return False
        return True

    def _request_json(self, http: urllib.request.Request) -> dict:
        try:
            with self._urlopen(http,timeout=self.timeout_seconds) as response:
                raw=response.read()
        except urllib.error.HTTPError as exc:
            # Do not include Authorization headers or access tokens in durable errors.
            raise GmailSendBoundaryError(f"Gmail HTTP {exc.code}") from exc
        except (urllib.error.URLError,TimeoutError,OSError) as exc:
            raise GmailSendBoundaryError(f"Gmail network failure: {type(exc).__name__}: {exc}") from exc
        try:
            data=json.loads(raw.decode("utf-8"))
        except Exception as exc:
            # After POST this is intentionally ambiguous: Gmail may have accepted the send.
            raise GmailSendBoundaryError("Gmail returned unreadable JSON") from exc
        if not isinstance(data,dict):
            raise GmailSendBoundaryError("Gmail response must be a JSON object")
        return data

    def _auth_headers(self, *, json_body: bool=False) -> dict[str,str]:
        headers={
            "Authorization":f"Bearer {self.access_token}",
            "Accept":"application/json",
            "User-Agent":"stillpoint-core/patch008",
        }
        if json_body:
            headers["Content-Type"]="application/json"
        return headers

    def _mime(self, request: ActionRequest, body: bytes) -> bytes:
        sender,recipient,subject=self._bound(request)
        try:
            text=body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise GmailSendBoundaryError("authorized email artifact is not UTF-8 text") from exc
        msg=EmailMessage()
        msg["From"]=sender
        msg["To"]=recipient
        msg["Subject"]=subject
        msg["Message-ID"]=_message_id(request)
        msg["X-StillPoint-Action-ID"]=request.action_id
        msg["X-StillPoint-Warrant-ID"]=request.warrant_id or ""
        msg.set_content(text)
        return msg.as_bytes(policy=SMTP)

    def execute(self, request: ActionRequest) -> ActionResult:
        if not self.enabled:
            raise GmailSendBoundaryError("gmail_send adapter is disabled")
        if not request.warrant_id:
            raise GmailSendBoundaryError("bound warrant required")
        if request.approval_required and not request.approval_id:
            raise GmailSendBoundaryError("approval required")
        if not request.permitted():
            raise GmailSendBoundaryError("approval or warrant expired")

        sender,recipient,subject=self._bound(request)
        ref,body=self._source(request)
        mime=self._mime(request,body)
        raw=base64.urlsafe_b64encode(mime).decode("ascii")
        endpoint=_SEND_ENDPOINT.format(user_id=urllib.parse.quote(sender,safe=""))
        http=urllib.request.Request(
            endpoint,
            data=json.dumps({"raw":raw},separators=(",",":")).encode("utf-8"),
            headers=self._auth_headers(json_body=True),
            method="POST",
        )

        # Deliberately no automatic retry. The runtime has already crossed the durable
        # dispatch boundary before this call, so any ambiguity must reconcile instead.
        data=self._request_json(http)
        provider_message_id=str(data.get("id") or "").strip()
        thread_id=str(data.get("threadId") or "").strip()
        if not provider_message_id:
            raise GmailSendBoundaryError("Gmail send response missing message id")

        receipt={
            "schema":"stillpoint.gmail-send-receipt.v1",
            "provider":"gmail",
            "proof":"provider_acceptance_not_recipient_read_or_final_delivery",
            "adapter":self.name,
            "action_id":request.action_id,
            "warrant_id":request.warrant_id,
            "approval_id":request.approval_id,
            "idempotency_key":request.idempotency_key,
            "sender":sender,
            "recipient":recipient,
            "subject_sha256":_sha(subject.encode("utf-8")),
            "rfc822_message_id":_message_id(request),
            "artifact":{
                "artifact_id":ref.artifact_id,
                "version":ref.version,
                "sha256":ref.sha256,
                "kind":ref.kind,
            },
            "mime_sha256":_sha(mime),
            "gmail_message_id":provider_message_id,
            "gmail_thread_id":thread_id,
        }
        canonical=json.dumps(receipt,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        return ActionResult(
            action_id=request.action_id,
            status="succeeded",
            evidence=[ActionEvidence(
                type="provider_acceptance_receipt",
                sha256=_sha(canonical.encode("utf-8")),
                note=canonical,
                satisfies="provider_acceptance_receipt",
            )],
            external_id=provider_message_id,
            adapter=self.name,
        )

    def probe_existing(self, request: ActionRequest) -> dict:
        """Read-only reconciliation probe for an already-uncertain Gmail send.

        Zero matches is kept ambiguous rather than treated as proof of no effect; this
        prevents eventual-consistency or indexing delay from silently authorizing retry.
        """
        if not self.enabled:
            raise GmailSendBoundaryError("gmail_send adapter is disabled")
        sender,recipient,subject=self._bound(request)
        msgid=_message_id(request)
        query=urllib.parse.urlencode({
            "q":f"rfc822msgid:{msgid} in:sent",
            "maxResults":"10",
        })
        endpoint=_LIST_ENDPOINT.format(user_id=urllib.parse.quote(sender,safe=""))+"?"+query
        http=urllib.request.Request(endpoint,headers=self._auth_headers(),method="GET")
        data=self._request_json(http)
        messages=data.get("messages") or []
        if not isinstance(messages,list):
            raise GmailSendBoundaryError("Gmail reconciliation response has invalid messages list")
        candidates=[m for m in messages if isinstance(m,dict) and m.get("id")]
        if len(candidates)!=1:
            return {
                "effect_occurred":None,
                "matches":[str(m.get("id")) for m in candidates],
                "evidence":[],
                "note":f"exact sent-mail Message-ID probe remains ambiguous ({len(candidates)} matches)",
            }

        message_id=str(candidates[0]["id"])
        params=urllib.parse.urlencode([
            ("format","metadata"),
            ("metadataHeaders","Message-ID"),
            ("metadataHeaders","From"),
            ("metadataHeaders","To"),
            ("metadataHeaders","Subject"),
        ])
        get_endpoint=_GET_ENDPOINT.format(
            user_id=urllib.parse.quote(sender,safe=""),
            message_id=urllib.parse.quote(message_id,safe=""),
        )+"?"+params
        metadata=self._request_json(urllib.request.Request(
            get_endpoint,headers=self._auth_headers(),method="GET"
        ))
        headers=_headers(metadata)
        exact=(
            headers.get("message-id")==msgid
            and parseaddr(headers.get("from", ""))[1].lower()==sender
            and parseaddr(headers.get("to", ""))[1].lower()==recipient
            and headers.get("subject")==subject
        )
        if not exact:
            return {
                "effect_occurred":None,
                "matches":[message_id],
                "evidence":[],
                "note":"Gmail Message-ID match did not reproduce the exact authorized headers",
            }

        receipt={
            "schema":"stillpoint.gmail-send-reconciliation.v1",
            "provider":"gmail",
            "action_id":request.action_id,
            "rfc822_message_id":msgid,
            "gmail_message_id":message_id,
            "gmail_thread_id":str(metadata.get("threadId") or candidates[0].get("threadId") or ""),
        }
        canonical=json.dumps(receipt,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        return {
            "effect_occurred":True,
            "matches":[message_id],
            "evidence":[ActionEvidence(
                type="gmail_send_reconciliation",
                sha256=_sha(canonical.encode("utf-8")),
                note=canonical,
                satisfies="",
            )],
            "note":f"exact Message-ID and authorized headers confirmed Gmail sent message {message_id}",
        }
