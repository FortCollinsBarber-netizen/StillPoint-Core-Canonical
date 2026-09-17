import json
import os
import sqlite3
import tempfile
import unittest
from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from stillpoint.signal_service import (
    ContinuationFactsSnapshot,
    SignalServiceConfig,
    SignalServiceConfigurationError,
    SnapshotFactsProvider,
    _require_delegation,
    _require_trigger,
    readiness,
)

NOW=datetime(2026,9,17,22,0,tzinfo=timezone.utc)
PAST=(NOW-timedelta(minutes=5)).isoformat()
FUT=(NOW+timedelta(minutes=5)).isoformat()


def env_for(tmp:Path):
    facts=tmp/'facts.json';facts.write_text(json.dumps({'observed_at':PAST,'valid_until':FUT,'source':'CEO','facts':{'company_policy_current':True},'envelopes':{'env1':{'condition':True}}}))
    return {
        'STILLPOINT_ROOT':str(tmp),
        'STILLPOINT_PROVIDER':'xai','XAI_API_KEY':'secret-xai','STILLPOINT_MODEL':'grok-test',
        'STILLPOINT_GMAIL_ACCOUNT':'signal@example.com','STILLPOINT_GMAIL_ACCESS_TOKEN':'secret-gmail','STILLPOINT_ENABLE_GMAIL_SEND':'1',
        'STILLPOINT_SIGNAL_DELEGATION_ID':'del-signal','STILLPOINT_SIGNAL_GMAIL_TRIGGER_ID':'trig-gmail','STILLPOINT_SIGNAL_FACTS_FILE':str(facts),
    }

class DB:
    def __init__(self):
        self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row
    def _connection(self):return self.c

class TestConfig(unittest.TestCase):
    def test_config_requires_explicit_live_boundaries_and_redacts_secret(self):
        with tempfile.TemporaryDirectory() as td:
            cfg=SignalServiceConfig.from_env(env_for(Path(td)))
            self.assertEqual(cfg.gmail_account,'signal@example.com')
            self.assertEqual(cfg.delegation_id,'del-signal')
            shown=json.dumps(cfg.redacted())
            self.assertNotIn('secret-gmail',shown);self.assertIn('gmail_access_token_configured',shown)

    def test_mock_provider_fails_closed_unless_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            e=env_for(Path(td));e['STILLPOINT_PROVIDER']='mock';e.pop('XAI_API_KEY')
            with self.assertRaises(SignalServiceConfigurationError):SignalServiceConfig.from_env(e)
            e['STILLPOINT_SIGNAL_ALLOW_MOCK']='1';cfg=SignalServiceConfig.from_env(e);self.assertEqual(cfg.provider_name,'mock')

    def test_facts_path_must_be_absolute(self):
        with tempfile.TemporaryDirectory() as td:
            e=env_for(Path(td));e['STILLPOINT_SIGNAL_FACTS_FILE']='facts.json'
            with self.assertRaises(SignalServiceConfigurationError):SignalServiceConfig.from_env(e)

    def test_heartbeat_must_be_shorter_than_lease(self):
        with tempfile.TemporaryDirectory() as td:
            e=env_for(Path(td));e['STILLPOINT_SIGNAL_LEASE_TTL_SECONDS']='20';e['STILLPOINT_SIGNAL_HEARTBEAT_SECONDS']='20'
            with self.assertRaises(SignalServiceConfigurationError):SignalServiceConfig.from_env(e)

class TestFacts(unittest.TestCase):
    def write(self,root,obj):
        p=Path(root)/'facts.json';p.write_text(json.dumps(obj));return p
    def test_current_snapshot_loads_and_preserves_envelope_facts(self):
        with tempfile.TemporaryDirectory() as td:
            p=self.write(td,{'observed_at':PAST,'valid_until':FUT,'facts':{'ok':True},'envelopes':{'env':{'visible':True}}})
            s=ContinuationFactsSnapshot.load(p,now_iso=NOW.isoformat());self.assertTrue(s.facts['ok']);self.assertTrue(s.envelopes['env']['visible'])
    def test_expired_snapshot_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p=self.write(td,{'observed_at':(NOW-timedelta(hours=2)).isoformat(),'valid_until':(NOW-timedelta(hours=1)).isoformat(),'facts':{'ok':True}})
            with self.assertRaises(SignalServiceConfigurationError):ContinuationFactsSnapshot.load(p,now_iso=NOW.isoformat())
    def test_provider_reloads_snapshot_each_call(self):
        with tempfile.TemporaryDirectory() as td:
            p=self.write(td,{'observed_at':PAST,'valid_until':FUT,'facts':{'revision':1}});provider=SnapshotFactsProvider(p,now_fn=lambda:NOW)
            self.assertEqual(provider.continuation()['revision'],1)
            self.write(td,{'observed_at':PAST,'valid_until':FUT,'facts':{'revision':2}})
            self.assertEqual(provider.continuation()['revision'],2)

class TestReadinessBindings(unittest.TestCase):
    def test_trigger_must_be_exact_signal_gmail_event_and_current(self):
        db=DB();db.c.execute('create table trigger_definitions(trigger_id text,status text,owner_role text,trigger_kind text,source text,event_type text,valid_from text,review_by text)')
        db.c.execute("insert into trigger_definitions values('trig','active','signal','event','gmail','message_received',?,?)",(PAST,FUT));db.c.commit()
        cfg=SimpleNamespace(trigger_id='trig')
        row=_require_trigger(db,cfg,now_iso=NOW.isoformat());self.assertEqual(row['owner_role'],'signal')
        db.c.execute("update trigger_definitions set owner_role='ledger'");db.c.commit()
        with self.assertRaises(SignalServiceConfigurationError):_require_trigger(db,cfg,now_iso=NOW.isoformat())

    def test_delegation_must_be_signal_current_and_include_send_email(self):
        C=lambda k,o,e:SimpleNamespace(key=k,operator=SimpleNamespace(value=o),expected=e)
        d=SimpleNamespace(status=SimpleNamespace(value='active'),delegate_role='signal',valid_from=PAST,review_by=FUT,allowed_action_types=['send_email'],execution_conditions=[C('signal_email.account','eq','signal@example.com'),C('signal_email.prepared','eq',True),C('signal_email.requires_human','eq',False),C('signal_email.classification','in',['scheduling'])])
        store=SimpleNamespace(get=lambda i:d);cfg=SimpleNamespace(delegation_id='d',gmail_account='signal@example.com')
        self.assertIs(_require_delegation(store,cfg,now_iso=NOW.isoformat()),d)
        d.allowed_action_types=[]
        with self.assertRaises(SignalServiceConfigurationError):_require_delegation(store,cfg,now_iso=NOW.isoformat())

    def test_readiness_never_exposes_access_token(self):
        with tempfile.TemporaryDirectory() as td:
            cfg=SignalServiceConfig.from_env(env_for(Path(td)))
            class Assembly:
                def __init__(self):
                    self.db=SimpleNamespace(schema_version=18)
                    self.facts=SimpleNamespace(snapshot=lambda:SimpleNamespace(observed_at=PAST,valid_until=FUT,source='CEO'))
                def close(self):pass
            out=readiness(cfg,now_fn=lambda:NOW,validator=lambda config,now_fn:{'ready':True,'schema_version':18,'continuation_facts':{'observed_at':PAST,'valid_until':FUT,'source':'CEO'}})
            self.assertTrue(out['ready']);self.assertNotIn('secret-gmail',json.dumps(out))

    def test_readiness_validator_is_observational_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            cfg=SignalServiceConfig.from_env(env_for(Path(td)));calls=[]
            def validator(config,now_fn):calls.append('validate');return {'ready':True,'schema_version':18}
            out=readiness(cfg,now_fn=lambda:NOW,validator=validator)
            self.assertTrue(out['ready']);self.assertEqual(calls,['validate'])

if __name__=='__main__':unittest.main()
