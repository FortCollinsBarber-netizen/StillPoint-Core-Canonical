"""Provider-neutral mail contracts for Signal.

Mail transport is not authority. These objects preserve provider/mailbox identity
and normalize inbound evidence so Gmail, iCloud, or later providers can sit under
the same StillPoint governance layer without sharing jurisdiction.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Protocol


@dataclass(frozen=True)
class MailboxIdentity:
    provider: str
    account: str
    jurisdiction: str

    def __post_init__(self) -> None:
        provider=(self.provider or "").strip().lower()
        account=(self.account or "").strip().lower()
        jurisdiction=(self.jurisdiction or "").strip().lower()
        if provider not in {"gmail","icloud"}:
            raise ValueError("unsupported mail provider")
        if "@" not in account:
            raise ValueError("explicit mailbox account required")
        if not jurisdiction:
            raise ValueError("mailbox jurisdiction required")
        object.__setattr__(self,"provider",provider)
        object.__setattr__(self,"account",account)
        object.__setattr__(self,"jurisdiction",jurisdiction)

    @property
    def authority_subject(self) -> str:
        return f"mailbox:{self.provider}:{self.account}:{self.jurisdiction}"

    def to_dict(self) -> dict[str,Any]:
        return asdict(self)


@dataclass(frozen=True)
class InboundMailMessage:
    provider: str
    account: str
    message_id: str
    provider_message_id: str
    thread_id: str = ""
    uid: str = ""
    from_address: str = ""
    from_header: str = ""
    reply_to: str = ""
    to: str = ""
    cc: str = ""
    subject: str = ""
    date: str = ""
    snippet: str = ""
    text_plain: str = ""
    text_plain_truncated: bool = False
    has_attachments: bool = False
    attachments: tuple[dict[str,Any], ...] = ()
    authentication_results: str = ""
    auto_submitted: str = ""
    precedence: str = ""
    list_unsubscribe: str = ""
    raw_sha256: str = ""
    observed_at: str = ""
    metadata: dict[str,Any] = field(default_factory=dict)

    def to_event_payload(self) -> dict[str,Any]:
        value=asdict(self)
        value["attachments"]=[dict(x) for x in self.attachments]
        return value


class MailInboxTransport(Protocol):
    identity: MailboxIdentity
    def fetch_since(self, cursor: str | None = None, *, limit: int = 50) -> tuple[list[InboundMailMessage], str]: ...


class MailSendTransport(Protocol):
    identity: MailboxIdentity
    name: str
    action_types: tuple[str, ...]
    def can_execute(self, request) -> bool: ...
    def execute(self, request): ...
