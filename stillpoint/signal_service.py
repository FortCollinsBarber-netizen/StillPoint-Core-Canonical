"""Production assembly for the first StillPoint vertical employee: Signal email.

Patch 019 introduces no new authority primitive. It wires the already-earned
worker, trigger, Gmail intake, Signal preparation, standing-delegation, delegated
warrant, and production dispatch layers into a deployable service boundary.

Continuing-evidence rule: operational continuation facts are loaded from a
finite snapshot with explicit observation and validity times. A stale snapshot
fails closed; successful operation yesterday does not silently become authority
for today.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping


class SignalServiceConfigurationError(RuntimeError):
    pass


def _parse_time(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception as exc:
        raise SignalServiceConfigurationError(f"invalid timestamp: {value!r}") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise SignalServiceConfigurationError("timestamps must be timezone-aware")
    return dt.astimezone(timezone.utc)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _bool(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _positive_int(name: str, value: str | int | None, default: int) -> int:
    raw = default if value in (None, "") else value
    try:
        parsed = int(raw)
    except Exception as exc:
        raise SignalServiceConfigurationError(f"{name} must be an integer") from exc
    if parsed <= 0:
        raise SignalServiceConfigurationError(f"{name} must be positive")
    return parsed


def _positive_float(name: str, value: str | float | None, default: float) -> float:
    raw = default if value in (None, "") else value
    try:
        parsed = float(raw)
    except Exception as exc:
        raise SignalServiceConfigurationError(f"{name} must be numeric") from exc
    if parsed <= 0:
        raise SignalServiceConfigurationError(f"{name} must be positive")
    return parsed


@dataclass(frozen=True)
class SignalServiceConfig:
    root: Path
    provider_name: str
    model: str
    gmail_account: str
    gmail_access_token: str = field(repr=False)
    delegation_id: str = ""
    trigger_id: str = ""
    facts_file: Path = Path(".")
    worker_id: str = ""
    poll_interval_seconds: float = 10.0
    lease_ttl_seconds: int = 90
    heartbeat_interval_seconds: int = 20
    gmail_timeout_seconds: int = 30
    allow_mock_provider: bool = False

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "SignalServiceConfig":
        env = env or os.environ
        root = Path(env.get("STILLPOINT_ROOT") or Path.cwd()).expanduser().resolve()
        provider = (env.get("STILLPOINT_PROVIDER") or "xai").strip().lower()
        model = (env.get("STILLPOINT_SIGNAL_MODEL") or env.get("STILLPOINT_MODEL") or env.get("XAI_MODEL") or "").strip()
        account = (env.get("STILLPOINT_GMAIL_ACCOUNT") or "").strip().lower()
        token = (env.get("STILLPOINT_GMAIL_ACCESS_TOKEN") or "").strip()
        delegation = (env.get("STILLPOINT_SIGNAL_DELEGATION_ID") or "").strip()
        trigger = (env.get("STILLPOINT_SIGNAL_GMAIL_TRIGGER_ID") or "").strip()
        facts_raw = (env.get("STILLPOINT_SIGNAL_FACTS_FILE") or "").strip()
        allow_mock = _bool(env.get("STILLPOINT_SIGNAL_ALLOW_MOCK"))
        worker = (env.get("STILLPOINT_SIGNAL_WORKER_ID") or "").strip()
        if not worker:
            worker = f"signal-email:{socket.gethostname()}:{os.getpid()}"

        missing = []
        if "@" not in account:
            missing.append("STILLPOINT_GMAIL_ACCOUNT")
        if not token:
            missing.append("STILLPOINT_GMAIL_ACCESS_TOKEN")
        if not delegation:
            missing.append("STILLPOINT_SIGNAL_DELEGATION_ID")
        if not trigger:
            missing.append("STILLPOINT_SIGNAL_GMAIL_TRIGGER_ID")
        if not facts_raw:
            missing.append("STILLPOINT_SIGNAL_FACTS_FILE")
        if env.get("STILLPOINT_ENABLE_GMAIL_SEND", "0").strip() != "1":
            missing.append("STILLPOINT_ENABLE_GMAIL_SEND=1")
        if provider == "mock" and not allow_mock:
            raise SignalServiceConfigurationError(
                "production Signal refuses mock provider unless STILLPOINT_SIGNAL_ALLOW_MOCK=1"
            )
        if provider == "xai" and not (env.get("XAI_API_KEY") or "").strip():
            missing.append("XAI_API_KEY")
        if not model:
            model = "grok-4.6" if provider == "xai" else "default"
        if missing:
            raise SignalServiceConfigurationError("missing/invalid Signal service configuration: " + ", ".join(missing))

        facts = Path(facts_raw).expanduser()
        if not facts.is_absolute():
            raise SignalServiceConfigurationError("STILLPOINT_SIGNAL_FACTS_FILE must be absolute")
        if facts.is_symlink():
            raise SignalServiceConfigurationError("STILLPOINT_SIGNAL_FACTS_FILE may not be a symlink")

        ttl = _positive_int("STILLPOINT_SIGNAL_LEASE_TTL_SECONDS", env.get("STILLPOINT_SIGNAL_LEASE_TTL_SECONDS"), 90)
        hb = _positive_int("STILLPOINT_SIGNAL_HEARTBEAT_SECONDS", env.get("STILLPOINT_SIGNAL_HEARTBEAT_SECONDS"), 20)
        if hb >= ttl:
            raise SignalServiceConfigurationError("heartbeat must be shorter than lease ttl")

        return cls(
            root=root,
            provider_name=provider,
            model=model,
            gmail_account=account,
            gmail_access_token=token,
            delegation_id=delegation,
            trigger_id=trigger,
            facts_file=facts.resolve(strict=False),
            worker_id=worker,
            poll_interval_seconds=_positive_float("STILLPOINT_SIGNAL_POLL_SECONDS", env.get("STILLPOINT_SIGNAL_POLL_SECONDS"), 10.0),
            lease_ttl_seconds=ttl,
            heartbeat_interval_seconds=hb,
            gmail_timeout_seconds=_positive_int("STILLPOINT_GMAIL_TIMEOUT_SECONDS", env.get("STILLPOINT_GMAIL_TIMEOUT_SECONDS"), 30),
            allow_mock_provider=allow_mock,
        )

    def redacted(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "provider_name": self.provider_name,
            "model": self.model,
            "gmail_account": self.gmail_account,
            "gmail_access_token_configured": bool(self.gmail_access_token),
            "delegation_id": self.delegation_id,
            "trigger_id": self.trigger_id,
            "facts_file": str(self.facts_file),
            "worker_id": self.worker_id,
            "poll_interval_seconds": self.poll_interval_seconds,
            "lease_ttl_seconds": self.lease_ttl_seconds,
            "heartbeat_interval_seconds": self.heartbeat_interval_seconds,
        }


@dataclass(frozen=True)
class ContinuationFactsSnapshot:
    observed_at: str
    valid_until: str
    facts: dict[str, Any]
    envelopes: dict[str, dict[str, Any]] = field(default_factory=dict)
    source: str = "operator"

    @classmethod
    def load(cls, path: Path, *, now_iso: str | None = None) -> "ContinuationFactsSnapshot":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise SignalServiceConfigurationError(f"continuation facts file not found: {path}") from exc
        except Exception as exc:
            raise SignalServiceConfigurationError(f"invalid continuation facts file: {path}") from exc
        if not isinstance(raw, dict):
            raise SignalServiceConfigurationError("continuation facts snapshot must be a JSON object")
        observed_at = str(raw.get("observed_at") or "")
        valid_until = str(raw.get("valid_until") or "")
        facts = raw.get("facts")
        envelopes = raw.get("envelopes") or {}
        source = str(raw.get("source") or "operator")
        if not observed_at or not valid_until or not isinstance(facts, dict) or not isinstance(envelopes, dict):
            raise SignalServiceConfigurationError(
                "facts snapshot requires observed_at, valid_until, facts object, and optional envelopes object"
            )
        observed = _parse_time(observed_at)
        valid = _parse_time(valid_until)
        now = _parse_time(now_iso) if now_iso else _now()
        if valid <= observed:
            raise SignalServiceConfigurationError("continuation facts valid_until must follow observed_at")
        if observed > now:
            raise SignalServiceConfigurationError("continuation facts observation is in the future")
        if now >= valid:
            raise SignalServiceConfigurationError("continuation facts snapshot is no longer current")
        return cls(observed_at=observed_at,valid_until=valid_until,facts=dict(facts),envelopes={str(k):dict(v) for k,v in envelopes.items()},source=source)


class SnapshotFactsProvider:
    """Reloads finite facts and revalidates their custody on every use."""
    def __init__(
        self,
        path: Path,
        *,
        now_fn: Callable[[], datetime] = _now,
        validator: Callable[[], None] | None = None,
    ):
        self.path=Path(path);self.now_fn=now_fn;self.validator=validator

    def snapshot(self) -> ContinuationFactsSnapshot:
        if self.validator is not None:
            self.validator()
        return ContinuationFactsSnapshot.load(self.path,now_iso=_iso(self.now_fn()))

    def continuation(self, **_: Any) -> dict[str, Any]:
        snap=self.snapshot()
        out=dict(snap.facts)
        out.setdefault("_stillpoint_observed_at",snap.observed_at)
        out.setdefault("_stillpoint_valid_until",snap.valid_until)
        out.setdefault("_stillpoint_source",snap.source)
        return out

    def envelope_facts(self, **_: Any) -> dict[str, dict[str, Any]]:
        return dict(self.snapshot().envelopes)


class _ReadOnlyDB:
    def __init__(self,path:Path):
        import sqlite3
        self.path=Path(path)
        if not self.path.is_file():
            raise SignalServiceConfigurationError(f"StillPoint database not found: {self.path}")
        try:
            self.conn=sqlite3.connect(f"file:{self.path}?mode=ro",uri=True)
        except Exception as exc:
            raise SignalServiceConfigurationError(f"cannot open StillPoint database read-only: {self.path}") from exc
        self.conn.row_factory=sqlite3.Row
    def _connection(self):return self.conn
    @property
    def schema_version(self)->int:
        try:row=self.conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
        except Exception as exc:raise SignalServiceConfigurationError("schema_migrations unavailable") from exc
        return int(row[0] or 0)
    def close(self):self.conn.close()

def validate_signal_service(config:SignalServiceConfig, *, now_fn:Callable[[],datetime]=_now, db_factory=None, delegation_store_factory=None, inspect_adapters_fn=None)->dict[str,Any]:
    """Side-effect-free readiness validation. Never registers a worker or calls Gmail/xAI."""
    now_iso=_iso(now_fn());facts=SnapshotFactsProvider(config.facts_file,now_fn=now_fn);snap=facts.snapshot()
    db=(db_factory or _ReadOnlyDB)(config.root/"state"/"company.sqlite")
    try:
        if int(db.schema_version)<18:raise SignalServiceConfigurationError(f"Signal service requires schema >=18, found {db.schema_version}")
        _require_trigger(db,config,now_iso=now_iso)
        if delegation_store_factory is None:
            from .authority.standing_store import StandingDelegationStore
            delegation_store=StandingDelegationStore(db)
        else:delegation_store=delegation_store_factory(db)
        delegation=_require_delegation(delegation_store,config,now_iso=now_iso)
        conn=db._connection()
        for envelope_id in delegation.claim_envelope_ids:
            row=conn.execute("SELECT status FROM temporal_claim_envelopes WHERE envelope_id=?",(envelope_id,)).fetchone()
            if not row or row["status"]!="active":raise SignalServiceConfigurationError(f"supporting claim envelope not current: {envelope_id}")
        if inspect_adapters_fn is None:
            from .adapters.production import inspect_production_adapters
            prod=inspect_production_adapters()
        else:prod=inspect_adapters_fn()
        if not prod.get("ok") or "gmail_send" not in (prod.get("enabled") or []):
            raise SignalServiceConfigurationError("gmail_send production adapter is not enabled and valid")
        return {"ready":True,"schema_version":db.schema_version,"delegation_id":config.delegation_id,"trigger_id":config.trigger_id,"continuation_facts":{"observed_at":snap.observed_at,"valid_until":snap.valid_until,"source":snap.source}}
    finally:db.close()

@dataclass
class SignalServiceAssembly:
    config: SignalServiceConfig
    db: Any
    runtime: Any
    employee: Any
    coordinator: Any
    facts: SnapshotFactsProvider

    def close(self) -> None:
        try:
            self.coordinator.stop_worker(self.config.worker_id)
        except Exception:
            pass
        try:
            self.db.close()
        except Exception:
            pass


def _require_trigger(db, config: SignalServiceConfig, *, now_iso: str) -> dict[str, Any]:
    row=db._connection().execute("SELECT * FROM trigger_definitions WHERE trigger_id=?",(config.trigger_id,)).fetchone()
    if not row:
        raise SignalServiceConfigurationError("configured Signal Gmail trigger does not exist")
    row=dict(row)
    if row.get("status")!="active" or row.get("owner_role")!="signal" or row.get("trigger_kind")!="event" or row.get("source")!="gmail" or row.get("event_type")!="message_received":
        raise SignalServiceConfigurationError("configured trigger is not an active Signal Gmail message trigger")
    now=_parse_time(now_iso)
    if now < _parse_time(row["valid_from"]) or now >= _parse_time(row["review_by"]):
        raise SignalServiceConfigurationError("configured Signal Gmail trigger is outside its review interval")
    return row


def _require_delegation(store, config: SignalServiceConfig, *, now_iso: str):
    delegation=store.get(config.delegation_id)
    if not delegation:
        raise SignalServiceConfigurationError("configured Signal standing delegation does not exist")
    status=getattr(delegation.status,"value",delegation.status)
    if status!="active" or delegation.delegate_role!="signal":
        raise SignalServiceConfigurationError("configured delegation is not active Signal standing")
    now=_parse_time(now_iso)
    if now < _parse_time(delegation.valid_from) or now >= _parse_time(delegation.review_by):
        raise SignalServiceConfigurationError("configured delegation is outside its review interval")
    if "send_email" not in delegation.allowed_action_types:
        raise SignalServiceConfigurationError("configured delegation does not include send_email")
    # Minimum machine-enforced execution constraints. Free-form exclusions are documentation;
    # production autonomy requires these conditions to be executable predicates.
    conditions=list(getattr(delegation,'execution_conditions',[]) or [])
    def has(key,operator=None,expected_marker=None):
        for c in conditions:
            op=getattr(getattr(c,'operator',None),'value',getattr(c,'operator',None))
            if getattr(c,'key',None)!=key:continue
            if operator is not None and op!=operator:continue
            if expected_marker is not None and getattr(c,'expected',None)!=expected_marker:continue
            return True
        return False
    if not has('signal_email.account','eq',config.gmail_account):
        raise SignalServiceConfigurationError('Signal delegation must bind signal_email.account to configured Gmail account')
    if not has('signal_email.prepared','eq',True):
        raise SignalServiceConfigurationError('Signal delegation must require signal_email.prepared=true')
    if not has('signal_email.requires_human','eq',False):
        raise SignalServiceConfigurationError('Signal delegation must require signal_email.requires_human=false')
    class_ok=False
    for c in conditions:
        op=getattr(getattr(c,'operator',None),'value',getattr(c,'operator',None))
        if getattr(c,'key',None)=='signal_email.classification' and op=='in' and isinstance(getattr(c,'expected',None),(list,tuple,set,frozenset)) and len(c.expected)>0:
            class_ok=True;break
    if not class_ok:
        raise SignalServiceConfigurationError('Signal delegation must explicitly allow a finite classification set')
    return delegation


def build_signal_service(config: SignalServiceConfig, *, now_fn: Callable[[], datetime] = _now) -> SignalServiceAssembly:
    """Assemble the live service from canonical StillPoint components.

    Imports are deliberately lazy so configuration/doctor commands can fail
    cleanly before network/provider initialization.
    """
    from .db import CompanyDB
    from .providers import make_provider
    from .registry import AgentRegistry
    from .runtime import CompanyRuntime
    from .adapters.production import build_production_registry, inspect_production_adapters
    from .adapters.gmail_inbox import SignalGmailInboxPoller
    from .workers import DurableWorkerCoordinator
    from .worker_service import PersistentWorkerService, WorkerServiceConfig
    from .triggers import TaskTriggerCoordinator
    from .signal_email import ProviderSignalResponder, SignalInboxExecutor
    from .temporal.envelope_store import ClaimEnvelopeStore
    from .authority.standing_store import StandingDelegationStore
    from .authority.delegated_warrants import DelegatedWarrantIssuer
    from .signal_autonomy import SignalStandingAuthorizer
    from .signal_employee import SignalEmailEmployee

    # Validate against a read-only connection first. Assembly begins only after all
    # governance/configuration boundaries are known to be current.
    validate_signal_service(config,now_fn=now_fn)
    db=CompanyDB(config.root/"state"/"company.sqlite")
    coordinator=None
    worker_registered=False
    try:
        now_iso=_iso(now_fn())
        facts=SnapshotFactsProvider(config.facts_file,now_fn=now_fn)
        triggers=TaskTriggerCoordinator(db)
        delegation_store=StandingDelegationStore(db)
        provider=make_provider(config.provider_name)
        config_path=config.root/"config"/"agents.json"
        if not config_path.is_file():
            config_path=Path(__file__).resolve().parent/"defaults"/"agents.json"
        runtime=CompanyRuntime(root=config.root,db=db,registry=AgentRegistry(config_path),provider=provider,default_model=config.model,smart_routing=False,allowed_import_roots=[config.root])
        adapters=build_production_registry(runtime)
        coordinator=DurableWorkerCoordinator(db)
        coordinator.register_worker(role="signal",worker_id=config.worker_id,metadata={"service":"signal_email","gmail_account":config.gmail_account},now_iso=now_iso)
        worker_registered=True
        db_path=config.root/"state"/"company.sqlite"
        def coordinator_factory():
            child_db=CompanyDB(db_path)
            return DurableWorkerCoordinator(child_db)
        worker=PersistentWorkerService(db=db,coordinator=coordinator,coordinator_factory=coordinator_factory,config=WorkerServiceConfig(role="signal",lease_ttl_seconds=config.lease_ttl_seconds,heartbeat_interval_seconds=config.heartbeat_interval_seconds,auto_retry_failed=False,triggered_only=True),worker_id=config.worker_id)
        poller=SignalGmailInboxPoller(db=db,trigger_coordinator=triggers,account=config.gmail_account,access_token=config.gmail_access_token,timeout_seconds=config.gmail_timeout_seconds)
        responder=ProviderSignalResponder(provider,model=config.model)
        preparer=SignalInboxExecutor(db=db,trigger_coordinator=triggers,account=config.gmail_account,responder=responder)
        envelope_store=ClaimEnvelopeStore(db)
        issuer=DelegatedWarrantIssuer(db)
        authorizer=SignalStandingAuthorizer(db=db,delegation_store=delegation_store,envelope_store=envelope_store,warrant_issuer=issuer)
        employee=SignalEmailEmployee(poller=poller,worker_service=worker,preparer=preparer,authorizer=authorizer,runtime=runtime,adapter_registry=adapters,delegation_id=config.delegation_id,continuation_facts_provider=facts.continuation,envelope_facts_provider=facts.envelope_facts,now_fn=now_fn)
        return SignalServiceAssembly(config=config,db=db,runtime=runtime,employee=employee,coordinator=coordinator,facts=facts)
    except Exception:
        if worker_registered and coordinator is not None:
            try:coordinator.stop_worker(config.worker_id)
            except Exception:pass
        db.close();raise


def readiness(config: SignalServiceConfig, *, now_fn: Callable[[], datetime] = _now, validator=validate_signal_service) -> dict[str, Any]:
    checks={"config":config.redacted(),"ready":False}
    try:
        result=validator(config,now_fn=now_fn)
        checks.update(result);checks["ready"]=bool(result.get("ready"))
        return checks
    except Exception as exc:
        checks["error"]=f"{type(exc).__name__}: {exc}"
        return checks


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(prog="python -m stillpoint.signal_service")
    sub=parser.add_subparsers(dest="cmd",required=True)
    sub.add_parser("check")
    sub.add_parser("once")
    serve=sub.add_parser("serve");serve.add_argument("--interval-seconds",type=float,default=None)
    args=parser.parse_args(argv)
    try:config=SignalServiceConfig.from_env()
    except Exception as exc:
        print(json.dumps({"ready":False,"error":f"{type(exc).__name__}: {exc}"},indent=2));return 2
    if args.cmd=="check":
        result=readiness(config);print(json.dumps(result,indent=2,default=str));return 0 if result.get("ready") else 1
    assembly=None
    try:
        assembly=build_signal_service(config)
        if args.cmd=="once":
            tick=assembly.employee.tick();print(json.dumps({"intake":tick.intake,"work":tick.work},indent=2,default=str));return 0
        interval=args.interval_seconds or config.poll_interval_seconds
        if interval<=0:raise SignalServiceConfigurationError("serve interval must be positive")
        assembly.employee.serve(interval_seconds=interval);return 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(json.dumps({"ready":False,"error":f"{type(exc).__name__}: {exc}"},indent=2));return 1
    finally:
        if assembly is not None:assembly.close()


if __name__=="__main__":
    raise SystemExit(main())
