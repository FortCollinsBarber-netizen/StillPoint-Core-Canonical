"""Common bounded-email parsing shared by mail transports."""
from __future__ import annotations
import re

_EMAIL_RE=re.compile(r"^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$")
_FROM_RE=re.compile(r"\bfrom\s+<?([^\s,;<>]+@[^\s,;<>]+\.[^\s,;<>]+)>?",re.I)
_TO_RE=re.compile(r"\bto\s+<?([^\s,;<>]+@[^\s,;<>]+\.[^\s,;<>]+)>?",re.I)
_SUBJECT_RE=re.compile(r"\bsubject\s*:\s*(.+)\s*$",re.I|re.S)

class MailBoundaryError(RuntimeError):
    pass

def parse_authorized_send_target(text:str)->tuple[str,str,str]:
    target=(text or "").strip();lowered=target.lower()
    for forbidden in (" cc:"," bcc:","\ncc:","\nbcc:","reply to","forward ","attachment","attach "):
        if forbidden in lowered: raise MailBoundaryError("bounded email does not authorize cc, bcc, forwarding, or attachments")
    fm=_FROM_RE.search(target);tm=_TO_RE.search(target);sm=_SUBJECT_RE.search(target)
    if not fm or not tm or not sm: raise MailBoundaryError("send_email target must explicitly include 'from SENDER to RECIPIENT subject: SUBJECT'")
    sender=fm.group(1).strip().lower();recipient=tm.group(1).strip().lower();subject=sm.group(1).strip()
    if not _EMAIL_RE.fullmatch(sender) or not _EMAIL_RE.fullmatch(recipient): raise MailBoundaryError("invalid authorized sender or recipient")
    if not subject or '\r' in subject or '\n' in subject or len(subject)>200: raise MailBoundaryError("invalid subject")
    addresses=re.findall(r"[^\s,;<>]+@[^\s,;<>]+\.[^\s,;<>]+",target)
    if len(addresses)!=2: raise MailBoundaryError("bounded email authorizes exactly one sender and one recipient")
    return sender,recipient,subject
