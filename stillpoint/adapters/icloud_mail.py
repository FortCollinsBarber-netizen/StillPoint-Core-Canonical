"""Bounded iCloud Mail transport for StillPoint Signal.

Uses Apple's documented iCloud Mail IMAP/SMTP endpoints. Credentials are injected
at runtime only. The real Apple Account password is never accepted by design; the
caller must provide a dedicated app-specific password or future supported token.

This adapter does not create authority. It executes only already-bound ActionRequests
and supplies read-only inbox evidence for higher Signal layers.
"""
from __future__ import annotations

import email
import hashlib
import imaplib
import json
import re
import smtplib
import ssl
from dataclasses import asdict
from datetime import datetime, timezone
from email.message import EmailMessage, Message
from email.policy import SMTP, default
from email.utils import parseaddr
from typing import Any, Callable

from ..contracts.models import ActionEvidence, ActionResult
from ..mail_contracts import InboundMailMessage, MailboxIdentity
from .mail_common import parse_authorized_send_target

IMAP_HOST="imap.mail.me.com"
IMAP_PORT=993
SMTP_HOST="smtp.mail.me.com"
SMTP_PORT=587
_EMAIL_RE=re.compile(r"^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$")
_ICLOUD_TRUSTED_AUTH_SERVICES=frozenset({"dmarc.icloud.com","dkim-verifier.icloud.com","spf.icloud.com"})


class ICloudMailBoundaryError(RuntimeError):
    pass


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _message_id(action_id: str) -> str:
    return f"<stillpoint-{action_id}@stillpoint.invalid>"

def _header(message: Message, name: str) -> str:
    value=message.get(name)
    return str(value or "").strip()

def _headers(message: Message, name: str) -> tuple[str,...]:
    values=message.get_all(name,[]) or []
    return tuple(str(value or "").strip() for value in values if str(value or "").strip())

def _authserv_id(value: str) -> str:
    return str(value or "").split(";",1)[0].strip().lower()

def _receiver_trace_values(message: Message, name: str) -> tuple[str,...]:
    wanted=name.lower();values=[]
    for field,value in message.raw_items():
        if field.lower()=="received":break
        if field.lower()==wanted and str(value or "").strip():values.append(str(value).strip())
    return tuple(values)

def _icloud_authentication_evidence(message: Message) -> tuple[str,dict[str,Any]]:
    auth=_headers(message,"Authentication-Results")
    receiver_auth=_receiver_trace_values(message,"Authentication-Results")
    trusted=tuple(value for value in receiver_auth if _authserv_id(value) in _ICLOUD_TRUSTED_AUTH_SERVICES)
    arc=_headers(message,"ARC-Authentication-Results")
    received_spf=_headers(message,"Received-SPF")
    trace=[];receiver_side=True
    for field,value in message.raw_items():
        lower=field.lower()
        if lower=="received":receiver_side=False
        if lower in {"authentication-results","arc-authentication-results","received-spf"}:
            trace.append({"header":field,"value":str(value or "").strip(),"receiver_side":receiver_side})
    evidence={
        "trusted_authentication_results":list(trusted),
        "receiver_authentication_results":list(receiver_auth),
        "all_authentication_results":list(auth),
        "arc_authentication_results":list(arc),
        "received_spf":list(received_spf),
        "authentication_trace":trace,
        "trusted_authserv_ids":sorted(_ICLOUD_TRUSTED_AUTH_SERVICES),
        "trust_boundary":"receiver trace headers before first Received plus exact iCloud authserv-id",
    }
    return "; ".join(trusted),evidence

def _address(value: str) -> str:
    return parseaddr(value or "")[1].lower()

def _plain_body(message: Message, *, max_bytes: int) -> tuple[str,bool,bool,tuple[dict[str,Any],...]]:
    attachments=[]
    texts=[]
    total=0
    truncated=False
    for part in message.walk() if message.is_multipart() else [message]:
        disposition=(part.get_content_disposition() or "").lower()
        filename=part.get_filename()
        ctype=part.get_content_type()
        if disposition=="attachment" or filename:
            payload=part.get_payload(decode=True) or b""
            attachments.append({"filename":str(filename or ""),"content_type":ctype,"size_bytes":len(payload)})
            continue
        if ctype!="text/plain":
            continue
        payload=part.get_payload(decode=True)
        if payload is None:
            raw=part.get_payload()
            payload=str(raw or "").encode(part.get_content_charset() or "utf-8",errors="replace")
        room=max(0,max_bytes-total)
        if len(payload)>room:
            payload=payload[:room];truncated=True
        total+=len(payload)
        charset=part.get_content_charset() or "utf-8"
        texts.append(payload.decode(charset,errors="replace"))
        if total>=max_bytes:
            truncated=True;break
    return "\n".join(x for x in texts if x).strip(),truncated,bool(attachments),tuple(attachments)


class ICloudInboxTransport:
    """Read-only iCloud Inbox poller using monotonically increasing IMAP UIDs."""
    def __init__(self, *, account: str, app_password: str, jurisdiction: str,
                 imap_factory: Callable[...,Any]|None=None, timeout_seconds: int=30,
                 max_body_bytes: int=65536):
        account=(account or "").strip().lower()
        if not _EMAIL_RE.fullmatch(account): raise ICloudMailBoundaryError("explicit iCloud mailbox required")
        if not (app_password or "").strip(): raise ICloudMailBoundaryError("iCloud app-specific password required")
        self.identity=MailboxIdentity("icloud",account,jurisdiction)
        self.account=account;self.app_password=app_password.strip();self.timeout_seconds=int(timeout_seconds)
        self.max_body_bytes=int(max_body_bytes);self._imap_factory=imap_factory or imaplib.IMAP4_SSL

    def _connect(self):
        client=self._imap_factory(IMAP_HOST,IMAP_PORT,ssl_context=ssl.create_default_context(),timeout=self.timeout_seconds)
        # Apple documents the local-part username as normal for IMAP; some clients need full address.
        local=self.account.split("@",1)[0]
        try:
            typ,_=client.login(local,self.app_password)
            if str(typ).upper()!="OK":
                typ,_=client.login(self.account,self.app_password)
        except Exception:
            typ,_=client.login(self.account,self.app_password)
        if str(typ).upper()!="OK": raise ICloudMailBoundaryError("iCloud IMAP authentication failed")
        typ,_=client.select("INBOX",readonly=True)
        if str(typ).upper()!="OK": raise ICloudMailBoundaryError("cannot select iCloud INBOX read-only")
        return client

    def baseline_cursor(self) -> str:
        client=self._connect()
        try:
            typ,data=client.uid("search",None,"ALL")
            if str(typ).upper()!="OK": raise ICloudMailBoundaryError("iCloud baseline UID search failed")
            raw=(data[0] or b"") if data else b""
            uids=[]
            for value in raw.split():
                try:uids.append(int(value.decode("ascii") if isinstance(value,bytes) else str(value)))
                except Exception:raise ICloudMailBoundaryError("iCloud baseline contained invalid UID")
            return str(max(uids) if uids else 0)
        finally:
            try:client.logout()
            except Exception:pass

    @staticmethod
    def _search_uids(client, cursor: str|None, limit: int) -> list[str]:
        start=max(1,int(cursor or 0)+1)
        typ,data=client.uid("search",None,f"UID {start}:*")
        if str(typ).upper()!="OK": raise ICloudMailBoundaryError("iCloud UID search failed")
        raw=(data[0] or b"") if data else b""
        uids=[x.decode("ascii") if isinstance(x,bytes) else str(x) for x in raw.split()]
        return uids[:max(0,int(limit))]

    def fetch_since(self, cursor: str|None=None, *, limit: int=50) -> tuple[list[InboundMailMessage],str]:
        if cursor is None: raise ICloudMailBoundaryError("explicit cursor required; establish baseline first")
        client=self._connect();messages=[];last=str(cursor)
        try:
            for uid in self._search_uids(client,cursor,limit):
                typ,data=client.uid("fetch",uid,"(BODY.PEEK[])" )
                if str(typ).upper()!="OK": raise ICloudMailBoundaryError(f"iCloud fetch failed for UID {uid}")
                raw=b""
                for item in data or []:
                    if isinstance(item,tuple) and len(item)>1 and isinstance(item[1],(bytes,bytearray)): raw=bytes(item[1]);break
                if not raw: raise ICloudMailBoundaryError(f"iCloud message UID {uid} had no RFC822 body")
                msg=email.message_from_bytes(raw,policy=default)
                body,truncated,has_attach,attachments=_plain_body(msg,max_bytes=self.max_body_bytes)
                mid=_header(msg,"Message-ID") or f"icloud-uid-{uid}@{self.account}"
                auth,auth_evidence=_icloud_authentication_evidence(msg)
                messages.append(InboundMailMessage(
                    provider="icloud",account=self.account,message_id=mid,provider_message_id=uid,uid=uid,
                    from_address=_address(_header(msg,"From")),from_header=_header(msg,"From"),reply_to=_header(msg,"Reply-To"),
                    to=_header(msg,"To"),cc=_header(msg,"Cc"),subject=_header(msg,"Subject"),date=_header(msg,"Date"),
                    snippet=(body[:240] if body else ""),text_plain=body,text_plain_truncated=truncated,
                    has_attachments=has_attach,attachments=attachments,authentication_results=auth,
                    auto_submitted=_header(msg,"Auto-Submitted"),precedence=_header(msg,"Precedence"),
                    list_unsubscribe=_header(msg,"List-Unsubscribe"),raw_sha256=_sha(raw),observed_at=_now(),
                    metadata={"imap_host":IMAP_HOST,"imap_uid":uid,"read_only":True,"authentication_evidence":auth_evidence},
                ))
                last=uid
            return messages,last
        finally:
            try: client.logout()
            except Exception: pass


class ICloudSendAdapter:
    name="icloud_send"
    action_types=("send_email",)
    def __init__(self, *, db, account: str, app_password: str, jurisdiction: str,
                 enabled: bool=False, smtp_factory: Callable[...,Any]|None=None, imap_factory: Callable[...,Any]|None=None,
                 timeout_seconds: int=30):
        account=(account or "").strip().lower()
        if not _EMAIL_RE.fullmatch(account): raise ICloudMailBoundaryError("explicit iCloud mailbox required")
        if enabled and not (app_password or "").strip(): raise ICloudMailBoundaryError("iCloud app-specific password required")
        self.db=db;self.account=account;self.app_password=(app_password or "").strip();self.enabled=bool(enabled)
        self.identity=MailboxIdentity("icloud",account,jurisdiction);self._smtp_factory=smtp_factory or smtplib.SMTP;self._imap_factory=imap_factory or imaplib.IMAP4_SSL;self.timeout_seconds=int(timeout_seconds)

    def _bound(self,request):
        if request.action_type!="send_email": raise ICloudMailBoundaryError("unsupported action type")
        if len(request.artifact_refs)!=1: raise ICloudMailBoundaryError("iCloud send requires exactly one authorized artifact")
        sender,recipient,subject=parse_authorized_send_target(request.target)
        if sender!=self.account: raise ICloudMailBoundaryError("authorized sender does not match configured iCloud account")
        if request.target not in request.scope: raise ICloudMailBoundaryError("authorized target missing from ActionRequest scope")
        return sender,recipient,subject

    def _source(self,request):
        ref=request.artifact_refs[0]
        if not ref.artifact_id: raise ICloudMailBoundaryError("artifact id required")
        row=self.db.get_artifact(ref.artifact_id)
        if not row or row["task_id"]!=request.task_id or int(row["version"])!=int(ref.version) or row["sha256"]!=ref.sha256:
            raise ICloudMailBoundaryError("authorized artifact binding mismatch")
        run=self.db.get_run(row["produced_by_run_id"])
        if not run: raise ICloudMailBoundaryError("artifact source run missing")
        body=str(run["output"]).encode("utf-8")
        if _sha(body)!=ref.sha256: raise ICloudMailBoundaryError("artifact content hash mismatch")
        return ref,body

    def can_execute(self,request)->bool:
        if not self.enabled:return False
        try:self._bound(request);self._source(request)
        except Exception:return False
        return True

    def _mime(self,request,body:bytes)->EmailMessage:
        sender,recipient,subject=self._bound(request)
        try:text=body.decode("utf-8")
        except UnicodeDecodeError as exc: raise ICloudMailBoundaryError("authorized email artifact is not UTF-8") from exc
        msg=EmailMessage();msg["From"]=sender;msg["To"]=recipient;msg["Subject"]=subject
        msg["Message-ID"]=_message_id(request.action_id);msg["X-StillPoint-Action-ID"]=request.action_id;msg["X-StillPoint-Warrant-ID"]=request.warrant_id or "";msg.set_content(text)
        return msg

    def execute(self,request)->ActionResult:
        if not self.enabled: raise ICloudMailBoundaryError("icloud_send adapter is disabled")
        if not request.warrant_id: raise ICloudMailBoundaryError("bound warrant required")
        if request.approval_required and not request.approval_id: raise ICloudMailBoundaryError("approval required")
        if not request.permitted(): raise ICloudMailBoundaryError("approval or warrant expired")
        sender,recipient,subject=self._bound(request);ref,body=self._source(request);msg=self._mime(request,body)
        # No automatic retries. Runtime has already crossed the durable dispatch boundary.
        smtp=self._smtp_factory(SMTP_HOST,SMTP_PORT,timeout=self.timeout_seconds)
        try:
            smtp.ehlo();smtp.starttls(context=ssl.create_default_context());smtp.ehlo();smtp.login(self.account,self.app_password)
            refused=smtp.send_message(msg,from_addr=sender,to_addrs=[recipient]) or {}
            if refused: raise ICloudMailBoundaryError("iCloud SMTP refused authorized recipient")
        except ICloudMailBoundaryError: raise
        except Exception as exc: raise ICloudMailBoundaryError(f"iCloud SMTP dispatch failed: {type(exc).__name__}: {exc}") from exc
        finally:
            try:smtp.quit()
            except Exception:pass
        receipt={"schema":"stillpoint.icloud-send-receipt.v1","provider":"icloud","proof":"smtp_provider_acceptance_not_recipient_read_or_final_delivery","adapter":self.name,"action_id":request.action_id,"warrant_id":request.warrant_id,"approval_id":request.approval_id,"idempotency_key":request.idempotency_key,"sender":sender,"recipient":recipient,"subject_sha256":_sha(subject.encode()),"rfc822_message_id":_message_id(request.action_id),"artifact":{"artifact_id":ref.artifact_id,"version":ref.version,"sha256":ref.sha256,"kind":ref.kind},"smtp_host":SMTP_HOST,"smtp_port":SMTP_PORT}
        canonical=json.dumps(receipt,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        return ActionResult(action_id=request.action_id,status="succeeded",evidence=[ActionEvidence(type="provider_acceptance_receipt",sha256=_sha(canonical.encode()),note=canonical,satisfies="provider_acceptance_receipt")],external_id=_message_id(request.action_id),adapter=self.name)


    def _imap_login(self):
        client=self._imap_factory(IMAP_HOST,IMAP_PORT,ssl_context=ssl.create_default_context(),timeout=self.timeout_seconds)
        local=self.account.split('@',1)[0]
        try:
            typ,_=client.login(local,self.app_password)
            if str(typ).upper()!='OK':typ,_=client.login(self.account,self.app_password)
        except Exception:
            typ,_=client.login(self.account,self.app_password)
        if str(typ).upper()!='OK':raise ICloudMailBoundaryError('iCloud IMAP authentication failed')
        return client

    @staticmethod
    def _sent_mailbox(client)->str:
        typ,rows=client.list()
        if str(typ).upper()!='OK':raise ICloudMailBoundaryError('iCloud mailbox list failed')
        candidates=[]
        for raw in rows or []:
            text=raw.decode('utf-8','replace') if isinstance(raw,bytes) else str(raw)
            if '\\Sent' not in text:continue
            # RFC 3501 LIST response ends with the mailbox name. Quoted names are common.
            m=re.search(r'"([^"]+)"\s*$',text)
            name=m.group(1) if m else text.rsplit(' ',1)[-1].strip('"')
            if name:candidates.append(name)
        if len(candidates)!=1:raise ICloudMailBoundaryError(f'iCloud Sent mailbox discovery ambiguous ({len(candidates)} candidates)')
        return candidates[0]

    def probe_existing(self,request)->dict[str,Any]:
        """Read-only sent-mail reconciliation for an uncertain SMTP dispatch.

        Zero matches is ambiguous, never proof of no effect. Only one exact deterministic
        Message-ID with the authorized From/To/Subject can confirm provider-side effect.
        """
        sender,recipient,subject=self._bound(request);msgid=_message_id(request.action_id);client=self._imap_login()
        try:
            folder=self._sent_mailbox(client);typ,_=client.select(folder,readonly=True)
            if str(typ).upper()!='OK':raise ICloudMailBoundaryError('cannot select iCloud Sent mailbox read-only')
            typ,data=client.uid('search',None,'HEADER','Message-ID',msgid)
            if str(typ).upper()!='OK':raise ICloudMailBoundaryError('iCloud sent Message-ID search failed')
            raw=(data[0] or b'') if data else b'';uids=[x.decode('ascii') if isinstance(x,bytes) else str(x) for x in raw.split()]
            if len(uids)!=1:return {'effect_occurred':None,'matches':uids,'evidence':[],'note':f'exact iCloud sent-mail Message-ID probe remains ambiguous ({len(uids)} matches)'}
            uid=uids[0];typ,parts=client.uid('fetch',uid,'(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID FROM TO SUBJECT)])')
            if str(typ).upper()!='OK':raise ICloudMailBoundaryError('iCloud sent-header fetch failed')
            header_bytes=b''
            for item in parts or []:
                if isinstance(item,tuple) and len(item)>1 and isinstance(item[1],(bytes,bytearray)):header_bytes=bytes(item[1]);break
            if not header_bytes:return {'effect_occurred':None,'matches':[uid],'evidence':[],'note':'iCloud sent match had no readable headers'}
            msg=email.message_from_bytes(header_bytes,policy=default)
            exact=(_header(msg,'Message-ID')==msgid and _address(_header(msg,'From'))==sender and _address(_header(msg,'To'))==recipient and _header(msg,'Subject')==subject)
            if not exact:return {'effect_occurred':None,'matches':[uid],'evidence':[],'note':'iCloud Message-ID match did not reproduce exact authorized headers'}
            receipt={'schema':'stillpoint.icloud-send-reconciliation.v1','provider':'icloud','action_id':request.action_id,'rfc822_message_id':msgid,'imap_uid':uid,'sent_mailbox':folder}
            canonical=json.dumps(receipt,sort_keys=True,separators=(',',':'),ensure_ascii=False)
            return {'effect_occurred':True,'matches':[uid],'evidence':[ActionEvidence(type='icloud_send_reconciliation',sha256=_sha(canonical.encode()),note=canonical,satisfies='')],'note':f'exact Message-ID and authorized headers confirmed iCloud sent message UID {uid}'}
        finally:
            try:client.logout()
            except Exception:pass
