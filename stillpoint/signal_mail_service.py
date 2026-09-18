"""Provider-neutral production assembly for Signal mailboxes.

This is the Apple-first service path. Each process instance owns one exact mailbox
jurisdiction. A higher-level Signal fleet may supervise multiple instances, but
standing delegation, trigger, cursor, worker lease, and credentials remain separate.
"""
from __future__ import annotations

import hashlib,json,os,socket,uuid
from dataclasses import dataclass,field
from datetime import datetime,timezone
from pathlib import Path
from typing import Any,Callable,Mapping

from .mail_contracts import MailboxIdentity
from .signal_service import ContinuationFactsSnapshot,SnapshotFactsProvider,SignalServiceConfigurationError


def _now():return datetime.now(timezone.utc)
def _iso(dt):return dt.astimezone(timezone.utc).isoformat()
def _bool(v):return str(v or '').strip().lower() in {'1','true','yes','on'}
def _pos(name,v,default):
    try:x=int(default if v in (None,'') else v)
    except Exception as exc:raise SignalServiceConfigurationError(f'{name} must be integer') from exc
    if x<=0:raise SignalServiceConfigurationError(f'{name} must be positive')
    return x

@dataclass(frozen=True)
class SignalMailboxServiceConfig:
    root:Path
    model_provider:str
    model:str
    identity:MailboxIdentity
    credential:str=field(repr=False)
    delegation_id:str=''
    trigger_id:str=''
    governance_sha256:str=''
    facts_file:Path=Path('.')
    worker_id:str=''
    poll_interval_seconds:int=10
    lease_ttl_seconds:int=90
    heartbeat_interval_seconds:int=20
    timeout_seconds:int=30
    allow_mock_provider:bool=False

    @classmethod
    def from_env(cls, env:Mapping[str,str]|None=None):
        env=env or os.environ;root=Path(env.get('STILLPOINT_ROOT') or Path.cwd()).expanduser().resolve()
        provider=(env.get('STILLPOINT_MAIL_PROVIDER') or '').strip().lower();account=(env.get('STILLPOINT_MAIL_ACCOUNT') or '').strip().lower();jurisdiction=(env.get('STILLPOINT_MAIL_JURISDICTION') or '').strip().lower()
        try:identity=MailboxIdentity(provider,account,jurisdiction)
        except Exception as exc:raise SignalServiceConfigurationError(str(exc)) from exc
        credential=(env.get('STILLPOINT_ICLOUD_APP_PASSWORD') if provider=='icloud' else env.get('STILLPOINT_GMAIL_ACCESS_TOKEN')) or ''
        credential=credential.strip();delegation=(env.get('STILLPOINT_SIGNAL_DELEGATION_ID') or '').strip();trigger=(env.get('STILLPOINT_SIGNAL_MAIL_TRIGGER_ID') or '').strip();governance=(env.get('STILLPOINT_SIGNAL_GOVERNANCE_SHA256') or '').strip().lower();facts_raw=(env.get('STILLPOINT_SIGNAL_FACTS_FILE') or '').strip()
        mp=(env.get('STILLPOINT_PROVIDER') or 'xai').strip().lower();allow_mock=_bool(env.get('STILLPOINT_SIGNAL_ALLOW_MOCK'));model=(env.get('STILLPOINT_SIGNAL_MODEL') or env.get('STILLPOINT_MODEL') or env.get('XAI_MODEL') or '').strip()
        missing=[]
        if not credential:missing.append('iCloud app-specific password' if provider=='icloud' else 'Gmail access token')
        if not delegation:missing.append('STILLPOINT_SIGNAL_DELEGATION_ID')
        if not trigger:missing.append('STILLPOINT_SIGNAL_MAIL_TRIGGER_ID')
        if len(governance)!=64 or any(ch not in '0123456789abcdef' for ch in governance):missing.append('STILLPOINT_SIGNAL_GOVERNANCE_SHA256')
        if not facts_raw:missing.append('STILLPOINT_SIGNAL_FACTS_FILE')
        if mp=='xai' and not (env.get('XAI_API_KEY') or '').strip():missing.append('XAI_API_KEY')
        if mp=='mock' and not allow_mock:raise SignalServiceConfigurationError('production Signal refuses mock provider unless explicitly allowed')
        if missing:raise SignalServiceConfigurationError('missing/invalid Signal mailbox configuration: '+', '.join(missing))
        facts=Path(facts_raw).expanduser()
        if not facts.is_absolute() or facts.is_symlink():raise SignalServiceConfigurationError('facts file must be an absolute non-symlink path')
        ttl=_pos('STILLPOINT_SIGNAL_LEASE_TTL_SECONDS',env.get('STILLPOINT_SIGNAL_LEASE_TTL_SECONDS'),90);hb=_pos('STILLPOINT_SIGNAL_HEARTBEAT_SECONDS',env.get('STILLPOINT_SIGNAL_HEARTBEAT_SECONDS'),20)
        if hb>=ttl:raise SignalServiceConfigurationError('heartbeat must be shorter than lease ttl')
        worker=(env.get('STILLPOINT_SIGNAL_WORKER_ID') or '').strip() or f"signal-mail:{provider}:{jurisdiction}:{socket.gethostname()}:{os.getpid()}"
        if not model:model='grok-4.6' if mp=='xai' else 'default'
        return cls(root=root,model_provider=mp,model=model,identity=identity,credential=credential,delegation_id=delegation,trigger_id=trigger,governance_sha256=governance,facts_file=facts.resolve(strict=False),worker_id=worker,poll_interval_seconds=_pos('STILLPOINT_SIGNAL_POLL_SECONDS',env.get('STILLPOINT_SIGNAL_POLL_SECONDS'),10),lease_ttl_seconds=ttl,heartbeat_interval_seconds=hb,timeout_seconds=_pos('STILLPOINT_MAIL_TIMEOUT_SECONDS',env.get('STILLPOINT_MAIL_TIMEOUT_SECONDS'),30),allow_mock_provider=allow_mock)

    def redacted(self):
        return {'root':str(self.root),'model_provider':self.model_provider,'model':self.model,'mailbox':self.identity.to_dict(),'credential_configured':bool(self.credential),'delegation_id':self.delegation_id,'trigger_id':self.trigger_id,'governance_sha256':self.governance_sha256,'facts_file':str(self.facts_file),'worker_id':self.worker_id,'poll_interval_seconds':self.poll_interval_seconds,'lease_ttl_seconds':self.lease_ttl_seconds,'heartbeat_interval_seconds':self.heartbeat_interval_seconds}


def _condition_match(delegation,key,operator,expected):
    for c in list(getattr(delegation,'execution_conditions',[]) or []):
        op=getattr(getattr(c,'operator',None),'value',getattr(c,'operator',None))
        if getattr(c,'key',None)==key and op==operator and getattr(c,'expected',None)==expected:return True
    return False

def _parse_time(value:str)->datetime:
    try:dt=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    except Exception as exc:raise SignalServiceConfigurationError(f'invalid timestamp: {value!r}') from exc
    if dt.tzinfo is None or dt.utcoffset() is None:raise SignalServiceConfigurationError('timestamp must be timezone-aware')
    return dt.astimezone(timezone.utc)

def validate_mailbox_delegation(delegation,identity:MailboxIdentity,*,now_iso:str|None=None):
    status=getattr(getattr(delegation,'status',None),'value',getattr(delegation,'status',None))
    if status!='active' or delegation.delegate_role!='signal':raise SignalServiceConfigurationError('delegation is not active Signal standing')
    now=_parse_time(now_iso) if now_iso else _now()
    if now<_parse_time(delegation.valid_from) or now>=_parse_time(delegation.review_by):raise SignalServiceConfigurationError('delegation is outside its review interval')
    required=[('signal_email.provider','eq',identity.provider),('signal_email.account','eq',identity.account),('signal_email.jurisdiction','eq',identity.jurisdiction),('signal_email.prepared','eq',True),('signal_email.requires_human','eq',False)]
    for key,op,expected in required:
        if not _condition_match(delegation,key,op,expected):raise SignalServiceConfigurationError(f'delegation missing exact mailbox execution condition: {key}')
    class_ok=any(getattr(c,'key',None)=='signal_email.classification' and getattr(getattr(c,'operator',None),'value',getattr(c,'operator',None))=='in' and bool(getattr(c,'expected',None)) for c in delegation.execution_conditions)
    if not class_ok:raise SignalServiceConfigurationError('delegation must contain finite classification set')
    return delegation

def _require_materialized_facts(db, config:SignalMailboxServiceConfig) -> dict[str,Any]:
    """Require exact DB↔filesystem custody before Signal may use governance facts."""
    c=db._connection()
    try:
        row=c.execute(
            """SELECT * FROM signal_governance_materializations
               WHERE governance_sha256=? AND facts_path=?""",
            (config.governance_sha256,str(config.facts_file)),
        ).fetchone()
    except Exception as exc:
        raise SignalServiceConfigurationError(
            "Signal operational custody schema unavailable"
        ) from exc
    if not row:
        raise SignalServiceConfigurationError(
            "Signal governance facts have no materialization custody record"
        )
    row=dict(row)
    if row.get("status")!="materialized":
        raise SignalServiceConfigurationError(
            f"Signal governance facts are not materialized: {row.get('status')}"
        )
    if row.get("delegation_id")!=config.delegation_id or row.get("trigger_id")!=config.trigger_id:
        raise SignalServiceConfigurationError(
            "Signal governance materialization does not match configured authority"
        )
    try:
        actual=hashlib.sha256(config.facts_file.read_bytes()).hexdigest()
    except Exception as exc:
        raise SignalServiceConfigurationError(
            "Signal governance facts file cannot be read for custody verification"
        ) from exc
    if actual!=row.get("facts_sha256"):
        raise SignalServiceConfigurationError(
            "Signal governance facts digest does not match materialized custody"
        )
    return row


def _record_signal_health(
    db,
    config:SignalMailboxServiceConfig,
    *,
    status:str,
    error:str="",
    detail:dict[str,Any]|None=None,
    occurred_at:str|None=None,
) -> None:
    if status not in {"healthy","degraded","recovered","stopped"}:
        raise ValueError(status)
    c=db._connection()
    try:
        c.execute("BEGIN IMMEDIATE")
        c.execute(
            """INSERT INTO signal_service_health_events(
               event_id,service,worker_id,status,error,detail_json,occurred_at
               ) VALUES(?,?,?,?,?,?,?)""",
            (
                uuid.uuid4().hex,
                "signal_mail",
                config.worker_id,
                status,
                error or None,
                json.dumps(detail or {},sort_keys=True),
                occurred_at or _iso(_now()),
            ),
        )
        c.commit()
    except Exception:
        c.rollback()
        raise

@dataclass
class SignalMailboxServiceAssembly:
    config:SignalMailboxServiceConfig
    db:Any
    runtime:Any
    employee:Any
    coordinator:Any
    facts:SnapshotFactsProvider
    def close(self):
        try:self.coordinator.stop_worker(self.config.worker_id)
        except Exception:pass
        try:self.db.close()
        except Exception:pass


def build_signal_mailbox_service(config:SignalMailboxServiceConfig,*,now_fn:Callable[[],datetime]=_now)->SignalMailboxServiceAssembly:
    from .db import CompanyDB
    from .providers import make_provider
    from .registry import AgentRegistry
    from .runtime import CompanyRuntime
    from .workers import DurableWorkerCoordinator
    from .worker_service import PersistentWorkerService,WorkerServiceConfig
    from .triggers import TaskTriggerCoordinator
    from .signal_email import ProviderSignalResponder,SignalInboxExecutor
    from .signal_mail import SignalMailPoller
    from .temporal.envelope_store import ClaimEnvelopeStore
    from .authority.standing_store import StandingDelegationStore
    from .authority.delegated_warrants import DelegatedWarrantIssuer
    from .signal_autonomy import SignalStandingAuthorizer
    from .signal_employee import SignalEmailEmployee
    from .adapters.registry import ActionAdapterRegistry
    from .adapters.icloud_mail import ICloudInboxTransport,ICloudSendAdapter
    from .adapters.gmail_send import GmailSendAdapter
    from .adapters.gmail_inbox import SignalGmailInboxPoller

    validate_signal_mailbox_service(config,now_fn=now_fn)
    db=CompanyDB(config.root/'state'/'company.sqlite');coordinator=None;registered=False
    try:
        if db.schema_version<23:raise SignalServiceConfigurationError(f'provider-neutral Signal requires schema >=23, found {db.schema_version}')
        custody_check=lambda:_require_materialized_facts(db,config)
        facts=SnapshotFactsProvider(config.facts_file,now_fn=now_fn,validator=custody_check);facts.snapshot();now_iso=_iso(now_fn());c=db._connection()
        trigger=c.execute('select * from trigger_definitions where trigger_id=?',(config.trigger_id,)).fetchone()
        if not trigger or trigger['status']!='active' or trigger['owner_role']!='signal' or trigger['trigger_kind']!='event' or trigger['source']!=config.identity.provider or trigger['event_type']!='message_received':raise SignalServiceConfigurationError('trigger does not match exact mailbox provider')
        if _parse_time(now_iso)<_parse_time(trigger['valid_from']) or _parse_time(now_iso)>=_parse_time(trigger['review_by']):raise SignalServiceConfigurationError('trigger is outside its review interval')
        ds=StandingDelegationStore(db);delegation=ds.get(config.delegation_id)
        if not delegation:raise SignalServiceConfigurationError('standing delegation not found')
        validate_mailbox_delegation(delegation,config.identity,now_iso=now_iso)
        for envelope_id in delegation.claim_envelope_ids:
            row=c.execute('select status from temporal_claim_envelopes where envelope_id=?',(envelope_id,)).fetchone()
            if not row or row['status']!='active':raise SignalServiceConfigurationError(f'supporting claim envelope not current: {envelope_id}')
        provider=make_provider(config.model_provider);config_path=config.root/'config'/'agents.json'
        if not config_path.is_file():config_path=Path(__file__).resolve().parent/'defaults'/'agents.json'
        runtime=CompanyRuntime(root=config.root,db=db,registry=AgentRegistry(config_path),provider=provider,default_model=config.model,smart_routing=False,allowed_import_roots=[config.root])
        triggers=TaskTriggerCoordinator(db)
        if config.identity.provider=='icloud':
            inbox_transport=ICloudInboxTransport(account=config.identity.account,app_password=config.credential,jurisdiction=config.identity.jurisdiction,timeout_seconds=config.timeout_seconds)
            poller=SignalMailPoller(db=db,trigger_coordinator=triggers,transport=inbox_transport,trigger_id=config.trigger_id)
            send=ICloudSendAdapter(db=db,account=config.identity.account,app_password=config.credential,jurisdiction=config.identity.jurisdiction,enabled=True,timeout_seconds=config.timeout_seconds)
        else:
            poller=SignalGmailInboxPoller(db=db,trigger_coordinator=triggers,account=config.identity.account,access_token=config.credential,timeout_seconds=config.timeout_seconds)
            send=GmailSendAdapter(db=db,account=config.identity.account,access_token=config.credential,enabled=True,timeout_seconds=config.timeout_seconds)
        adapters=ActionAdapterRegistry([send]);coordinator=DurableWorkerCoordinator(db);coordinator.register_worker(role='signal',worker_id=config.worker_id,metadata={'service':'signal_mail','provider':config.identity.provider,'account':config.identity.account,'jurisdiction':config.identity.jurisdiction},now_iso=now_iso);registered=True
        db_path=config.root/'state'/'company.sqlite'
        def coordinator_factory():return DurableWorkerCoordinator(CompanyDB(db_path))
        worker=PersistentWorkerService(db=db,coordinator=coordinator,coordinator_factory=coordinator_factory,config=WorkerServiceConfig(role='signal',lease_ttl_seconds=config.lease_ttl_seconds,heartbeat_interval_seconds=config.heartbeat_interval_seconds,auto_retry_failed=False,triggered_only=True),worker_id=config.worker_id)
        responder=ProviderSignalResponder(provider,model=config.model);preparer=SignalInboxExecutor(db=db,trigger_coordinator=triggers,account=config.identity.account,provider=config.identity.provider,jurisdiction=config.identity.jurisdiction,responder=responder)
        authorizer=SignalStandingAuthorizer(db=db,delegation_store=ds,envelope_store=ClaimEnvelopeStore(db),warrant_issuer=DelegatedWarrantIssuer(db))
        health_recorder=lambda **kw:_record_signal_health(db,config,**kw)
        employee=SignalEmailEmployee(poller=poller,worker_service=worker,preparer=preparer,authorizer=authorizer,runtime=runtime,adapter_registry=adapters,delegation_id=config.delegation_id,continuation_facts_provider=facts.continuation,envelope_facts_provider=facts.envelope_facts,health_recorder=health_recorder,now_fn=now_fn)
        return SignalMailboxServiceAssembly(config,db,runtime,employee,coordinator,facts)
    except Exception:
        if registered and coordinator is not None:
            try:coordinator.stop_worker(config.worker_id)
            except Exception:pass
        db.close();raise
class _ReadOnlyMailboxDB:
    def __init__(self,path:Path):
        import sqlite3
        self.path=Path(path)
        if not self.path.is_file():
            raise SignalServiceConfigurationError(f'StillPoint database not found: {self.path}')
        self.conn=sqlite3.connect(f'file:{self.path}?mode=ro',uri=True)
        self.conn.row_factory=sqlite3.Row
    def _connection(self):return self.conn
    @property
    def schema_version(self):
        row=self.conn.execute('SELECT MAX(version) FROM schema_migrations').fetchone()
        return int(row[0] or 0)
    def close(self):self.conn.close()

def validate_signal_mailbox_service(config:SignalMailboxServiceConfig,*,now_fn:Callable[[],datetime]=_now,db_factory=None):
    """Side-effect-free production readiness. Does not contact mail or the model provider."""
    now_iso=_iso(now_fn())
    db=(db_factory or _ReadOnlyMailboxDB)(config.root/'state'/'company.sqlite')
    try:
        if int(db.schema_version)<23:
            raise SignalServiceConfigurationError(f'provider-neutral Signal requires schema >=23, found {db.schema_version}')
        _require_materialized_facts(db,config)
        facts=SnapshotFactsProvider(
            config.facts_file,
            now_fn=now_fn,
            validator=lambda:_require_materialized_facts(db,config),
        )
        snap=facts.snapshot()
        c=db._connection()
        trigger=c.execute('select * from trigger_definitions where trigger_id=?',(config.trigger_id,)).fetchone()
        if not trigger or trigger['status']!='active' or trigger['owner_role']!='signal' or trigger['trigger_kind']!='event' or trigger['source']!=config.identity.provider or trigger['event_type']!='message_received':
            raise SignalServiceConfigurationError('trigger does not match exact mailbox provider')
        now=_parse_time(now_iso)
        if now<_parse_time(trigger['valid_from']) or now>=_parse_time(trigger['review_by']):
            raise SignalServiceConfigurationError('trigger is outside its review interval')
        try:meta=__import__('json').loads(trigger['metadata_json'] or '{}')
        except Exception:meta={}
        if meta.get('signal_mail_governance_sha256')!=config.governance_sha256:
            raise SignalServiceConfigurationError('trigger governance digest does not match configured approved digest')
        from .authority.standing_store import StandingDelegationStore
        delegation=StandingDelegationStore(db).get(config.delegation_id)
        if not delegation:
            raise SignalServiceConfigurationError('standing delegation not found')
        validate_mailbox_delegation(delegation,config.identity,now_iso=now_iso)
        marker=f'signal_mail_governance_spec:{config.governance_sha256}'
        if marker not in str(delegation.policy_basis):
            raise SignalServiceConfigurationError('standing delegation governance digest does not match configured approved digest')
        for envelope_id in delegation.claim_envelope_ids:
            row=c.execute('select status from temporal_claim_envelopes where envelope_id=?',(envelope_id,)).fetchone()
            if not row or row['status']!='active':
                raise SignalServiceConfigurationError(f'supporting claim envelope not current: {envelope_id}')
        return {
            'ready':True,
            'schema_version':db.schema_version,
            'mailbox':config.identity.to_dict(),
            'delegation_id':config.delegation_id,
            'trigger_id':config.trigger_id,
            'governance_sha256':config.governance_sha256,
            'continuation_facts':{'observed_at':snap.observed_at,'valid_until':snap.valid_until,'source':snap.source},
        }
    finally:
        db.close()

def readiness(config:SignalMailboxServiceConfig,*,now_fn:Callable[[],datetime]=_now,validator=validate_signal_mailbox_service):
    out={'ready':False,'config':config.redacted()}
    try:
        result=validator(config,now_fn=now_fn);out.update(result);out['ready']=bool(result.get('ready'));return out
    except Exception as exc:
        out['error']=f'{type(exc).__name__}: {exc}';return out

def main(argv=None)->int:
    import argparse,json
    parser=argparse.ArgumentParser(prog='stillpoint-signal-mail')
    sub=parser.add_subparsers(dest='cmd',required=True)
    sub.add_parser('check')
    sub.add_parser('once')
    serve=sub.add_parser('serve');serve.add_argument('--interval-seconds',type=float,default=None)
    args=parser.parse_args(argv)
    try:config=SignalMailboxServiceConfig.from_env()
    except Exception as exc:
        print(json.dumps({'ready':False,'error':f'{type(exc).__name__}: {exc}'},indent=2));return 2
    if args.cmd=='check':
        result=readiness(config);print(json.dumps(result,indent=2,default=str));return 0 if result.get('ready') else 1
    assembly=None
    try:
        assembly=build_signal_mailbox_service(config)
        if args.cmd=='once':
            tick=assembly.employee.tick();print(json.dumps({'intake':tick.intake,'work':tick.work},indent=2,default=str));return 0
        interval=args.interval_seconds or config.poll_interval_seconds
        if interval<=0:raise SignalServiceConfigurationError('serve interval must be positive')
        assembly.employee.serve(interval_seconds=interval);return 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(json.dumps({'ready':False,'error':f'{type(exc).__name__}: {exc}'},indent=2));return 1
    finally:
        if assembly is not None:assembly.close()

if __name__=='__main__':
    raise SystemExit(main())

