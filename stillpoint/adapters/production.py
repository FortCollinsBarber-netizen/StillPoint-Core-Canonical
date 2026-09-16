from __future__ import annotations

import os
import re
from pathlib import Path

from .gmail_send import GmailSendAdapter
from .outbox import BoundedOutboxAdapter
from .registry import ActionAdapterRegistry


class ProductionBoundaryConfigurationError(RuntimeError):
    pass


_EMAIL_RE=re.compile(r"^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$")


def _outbox_enabled() -> bool:
    return os.getenv("STILLPOINT_ENABLE_OUTBOX","0").strip()=="1"


def _gmail_send_enabled() -> bool:
    return os.getenv("STILLPOINT_ENABLE_GMAIL_SEND","0").strip()=="1"


def configured_outbox_root() -> Path:
    raw=os.getenv("STILLPOINT_OUTBOX_ROOT","").strip()
    if not raw:
        raise ProductionBoundaryConfigurationError(
            "export_artifact requires STILLPOINT_OUTBOX_ROOT before authorization"
        )
    path=Path(raw).expanduser()
    if not path.is_absolute():
        raise ProductionBoundaryConfigurationError(
            "STILLPOINT_OUTBOX_ROOT must be an absolute path"
        )
    if path.is_symlink():
        raise ProductionBoundaryConfigurationError(
            "STILLPOINT_OUTBOX_ROOT may not be a symlink"
        )
    return path.resolve(strict=False)


def configured_gmail_account(*, required: bool=True) -> str | None:
    account=os.getenv("STILLPOINT_GMAIL_ACCOUNT","").strip().lower()
    if not account:
        if required:
            raise ProductionBoundaryConfigurationError(
                "gmail_send requires STILLPOINT_GMAIL_ACCOUNT"
            )
        return None
    if not _EMAIL_RE.fullmatch(account):
        raise ProductionBoundaryConfigurationError(
            "STILLPOINT_GMAIL_ACCOUNT must be one explicit email address"
        )
    return account


def _gmail_token() -> str:
    token=os.getenv("STILLPOINT_GMAIL_ACCESS_TOKEN","").strip()
    if not token:
        raise ProductionBoundaryConfigurationError(
            "STILLPOINT_ENABLE_GMAIL_SEND=1 requires STILLPOINT_GMAIL_ACCESS_TOKEN"
        )
    return token


def inspect_production_adapters() -> dict:
    enabled=[]
    available_disabled=[]
    errors=[]
    data={"ok":True,"enabled":enabled}

    if _outbox_enabled():
        try:
            data["outbox_root"]=str(configured_outbox_root())
            enabled.append("bounded_outbox")
        except Exception as exc:
            errors.append(str(exc))
    else:
        available_disabled.append("bounded_outbox")
        raw=os.getenv("STILLPOINT_OUTBOX_ROOT","").strip()
        if raw:
            try:
                data["configured_outbox_root"]=str(configured_outbox_root())
            except Exception as exc:
                data["outbox_configuration_warning"]=str(exc)

    if _gmail_send_enabled():
        try:
            configured_gmail_account()
            _gmail_token()
            enabled.append("gmail_send")
            data["gmail_account_configured"]=True
            data["gmail_access_token_configured"]=True
        except Exception as exc:
            errors.append(str(exc))
    else:
        available_disabled.append("gmail_send")
        if os.getenv("STILLPOINT_GMAIL_ACCOUNT","").strip():
            try:
                configured_gmail_account()
                data["gmail_account_configured"]=True
            except Exception as exc:
                data["gmail_configuration_warning"]=str(exc)
        if os.getenv("STILLPOINT_GMAIL_ACCESS_TOKEN","").strip():
            data["gmail_access_token_configured"]=True

    data["available_disabled"]=available_disabled
    data["network_adapters_enabled"]=[name for name in enabled if name=="gmail_send"]
    data["note"]="gmail_send is one-message/one-recipient only; no Gmail delete/update/draft adapter is registered"
    if errors:
        data["ok"]=False
        data["errors"]=errors
    return data


def build_production_registry(runtime) -> ActionAdapterRegistry:
    status=inspect_production_adapters()
    if not status["ok"]:
        raise ProductionBoundaryConfigurationError(
            "; ".join(status.get("errors") or ["invalid production adapter configuration"])
        )
    adapters=[]
    if "bounded_outbox" in status["enabled"]:
        adapters.append(BoundedOutboxAdapter(
            db=runtime.db,
            outbox_root=Path(status["outbox_root"]),
            enabled=True,
        ))
    if "gmail_send" in status["enabled"]:
        adapters.append(GmailSendAdapter(
            db=runtime.db,
            account=configured_gmail_account(),
            access_token=_gmail_token(),
            enabled=True,
        ))
    return ActionAdapterRegistry(adapters)


def build_gmail_send_adapter(runtime) -> GmailSendAdapter:
    if not _gmail_send_enabled():
        raise ProductionBoundaryConfigurationError(
            "Gmail send reconciliation requires STILLPOINT_ENABLE_GMAIL_SEND=1"
        )
    return GmailSendAdapter(
        db=runtime.db,
        account=configured_gmail_account(),
        access_token=_gmail_token(),
        enabled=True,
    )


def reconcile_gmail_send(runtime, action_id: str) -> dict:
    row=runtime.db.get_action_request(action_id)
    if not row:
        raise KeyError(action_id)
    dispatch=runtime.db.get_action_dispatch(action_id)
    if not dispatch:
        raise RuntimeError("action has no durable dispatch")
    if dispatch["state"]!="uncertain":
        raise RuntimeError("Gmail send reconciliation is only valid for uncertain dispatches")
    if dispatch["adapter"]!="gmail_send":
        raise RuntimeError("uncertain dispatch was not executed by gmail_send")

    request=runtime._request_from_row(row)
    probe=build_gmail_send_adapter(runtime).probe_existing(request)
    if probe["effect_occurred"] is not True:
        return {
            "action_id":action_id,
            "status":"ambiguous",
            "note":probe["note"],
            "matches":probe.get("matches",[]),
        }

    reconciled=runtime.reconcile_action_dispatch(
        action_id,
        effect_occurred=True,
        evidence=probe.get("evidence") or [],
        note=probe["note"],
        reconciled_by="operator:gmail_send_exact_message_id_probe",
    )
    return {
        "action_id":action_id,
        "status":reconciled["state"],
        "probe":probe,
    }
