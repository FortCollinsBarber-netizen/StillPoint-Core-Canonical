from __future__ import annotations
import json,sqlite3,tempfile,unittest
from pathlib import Path

from stillpoint.mail_contracts import MailboxIdentity,InboundMailMessage
from stillpoint.signal_mail import SignalMailPoller,SignalMailboxFleet
from stillpoint.signal_mail_governance import MailboxGovernanceSpec,SignalMailboxGovernanceSet
from stillpoint.temporal.envelope import ContinuationCondition,ConditionOperator
from stillpoint.signal_email import SignalInboxExecutor
from stillpoint.signal_autonomy import SignalStandingAuthorizer

class Patch028Tests(unittest.TestCase):
    def test_migration_adds_provider_neutral_mailbox_state(self):
        con=sqlite3.connect(':memory:');con.row_factory=sqlite3.Row
        con.executescript('''
        create table trigger_definitions(trigger_id text primary key,owner_role text,trigger_kind text,source text,event_type text,status text);
        create table signal_email_decisions(decision_id text primary key,task_id text,event_id text,message_id text,account text,sender text,reply_target text,disposition text,classification text,requires_human integer,reason text,facts_json text,artifact_id text,action_id text,created_at text);
        ''')
        sql=Path(__file__).resolve().parents[1]/'migrations'/'019_provider_neutral_mailboxes.sql';con.executescript(sql.read_text())
        cols={r['name'] for r in con.execute('pragma table_info(signal_email_decisions)')}
        self.assertIn('mail_provider',cols);self.assertIn('mail_jurisdiction',cols)
        self.assertIsNotNone(con.execute("select name from sqlite_master where type='table' and name='signal_mailboxes'").fetchone())

    def _spec(self,identity,delegation):
        return MailboxGovernanceSpec(identity=identity,delegation_id=delegation,claim_envelope_ids=['env1'],allowed_classifications=['scheduling','acknowledgement','routine_information'],continuation_conditions=[ContinuationCondition('policy.current',ConditionOperator.EQ,True)],exclusions=['money'],release_conditions=['review due'],valid_from='2026-09-17T00:00:00+00:00',review_by='2026-10-17T00:00:00+00:00',policy_basis='ceo policy',purpose='routine mail')

    def test_standing_binds_provider_account_and_jurisdiction(self):
        identity=MailboxIdentity('icloud','owner@icloud.com','personal')
        standing=self._spec(identity,'d1').standing();facts={c.key:c.expected for c in standing.execution_conditions}
        self.assertEqual(facts['signal_email.provider'],'icloud');self.assertEqual(facts['signal_email.account'],'owner@icloud.com');self.assertEqual(facts['signal_email.jurisdiction'],'personal')

    def test_delegation_id_cannot_govern_two_mailboxes(self):
        a=self._spec(MailboxIdentity('icloud','a@icloud.com','personal'),'same')
        b=self._spec(MailboxIdentity('gmail','b@example.com','school'),'same')
        with self.assertRaises(ValueError):SignalMailboxGovernanceSet([a,b])

    def test_fleet_keeps_mailbox_failures_separate(self):
        class E:
            def __init__(self,v=None,err=None):self.v=v;self.err=err
            def tick(self):
                if self.err:raise RuntimeError(self.err)
                return self.v
        fleet=SignalMailboxFleet.from_employees([(MailboxIdentity('icloud','a@icloud.com','personal'),E('ok')),(MailboxIdentity('gmail','b@example.com','school'),E(err='down'))])
        result=fleet.tick_all();self.assertEqual(result['mailbox:icloud:a@icloud.com:personal'],'ok');self.assertEqual(result['mailbox:gmail:b@example.com:school']['status'],'degraded')

    def test_executor_rejects_cross_provider_event_before_model(self):
        class T:
            def context_for_task(self,task_id):return {'source':'gmail','event_type':'message_received','payload':{'provider':'gmail','account':'x@example.com','jurisdiction':'school','message_id':'m1'}}
        class DB:pass
        class R:
            def draft(self,*a,**k):raise AssertionError('model must not run')
        ex=SignalInboxExecutor(db=DB(),trigger_coordinator=T(),account='x@icloud.com',provider='icloud',jurisdiction='personal',responder=R())
        with self.assertRaises(ValueError):ex.execute('t1',now_iso='2026-09-17T12:00:00+00:00')

    def test_authorizer_exposes_provider_and_jurisdiction_to_standing(self):
        action={'id':'a1','action_type':'send_email','target':'x'}
        decision={'action_id':'a1','disposition':'draft_reply','requires_human':0,'classification':'scheduling','sender':'a@example.com','reply_target':'b@example.com','account':'owner@icloud.com','message_id':'m1','facts_json':'{}','mail_provider':'icloud','mail_jurisdiction':'personal'}
        class Row(dict):pass
        class C:
            def execute(self,sql,args):
                class Q:
                    def __init__(self,row):self.row=row
                    def fetchone(self):return Row(self.row)
                return Q(action if 'action_requests' in sql else decision)
        class DB:
            def _connection(self):return C()
        class Assessment:
            eligible_for_warrant_consideration=False
        class Delegation:
            delegate_role='signal';claim_envelope_ids=[]
            def assess(self,**kw):self.execution=kw['execution_facts'];return Assessment()
        d=Delegation()
        class DS:
            def get(self,i):return d
            def record_assessment(self,**kw):return 'ev1'
        class ES:
            def get(self,i):return None
        class WI:pass
        out=SignalStandingAuthorizer(db=DB(),delegation_store=DS(),envelope_store=ES(),warrant_issuer=WI()).authorize_prepared_reply(action_id='a1',delegation_id='d1',now_iso='2026-09-17T12:00:00+00:00',continuation_facts={})
        self.assertFalse(out['authorized']);self.assertEqual(d.execution['signal_email']['provider'],'icloud');self.assertEqual(d.execution['signal_email']['jurisdiction'],'personal')

    def test_generic_poller_emits_provider_scoped_event_and_cursor(self):
        con=sqlite3.connect(':memory:');con.row_factory=sqlite3.Row
        con.executescript('''
        create table trigger_definitions(trigger_id text primary key,owner_role text,trigger_kind text,source text,event_type text,status text);
        create table signal_email_decisions(decision_id text primary key,task_id text,event_id text,message_id text,account text,sender text,reply_target text,disposition text,classification text,requires_human integer,reason text,facts_json text,artifact_id text,action_id text,created_at text);
        insert into trigger_definitions values('ti','signal','event','icloud','message_received','active');
        ''')
        sql=Path(__file__).resolve().parents[1]/'migrations'/'019_provider_neutral_mailboxes.sql';con.executescript(sql.read_text())
        class DB:
            def _connection(self):return con
        class Triggers:
            def __init__(self):self.events=[]
            def ingest_event(self,**kw):
                self.events.append(kw)
                class E:event_id='ev1'
                return E()
            def fire_event(self,event_id,now_iso):return ['task1']
        class Transport:
            identity=MailboxIdentity('icloud','owner@icloud.com','personal')
            def fetch_since(self,cursor,limit=50):
                m=InboundMailMessage(provider='icloud',account='owner@icloud.com',message_id='<m1>',provider_message_id='41',from_address='a@example.com',text_plain='Hi',authentication_results='dmarc=pass',observed_at='2026-09-17T12:00:00+00:00')
                return [m],'41'
        t=Triggers();p=SignalMailPoller(db=DB(),trigger_coordinator=t,transport=Transport(),trigger_id='ti')
        out=p.poll(now_iso='2026-09-17T12:00:01+00:00')
        self.assertEqual(out['cursor'],'41');self.assertEqual(out['tasks_created'],1);self.assertEqual(t.events[0]['source'],'icloud');self.assertEqual(t.events[0]['payload']['jurisdiction'],'personal')

if __name__=='__main__':unittest.main()
