from __future__ import annotations
import sqlite3,unittest
from email.message import EmailMessage
from pathlib import Path

from stillpoint.adapters.icloud_mail import ICloudInboxTransport
from stillpoint.mail_contracts import MailboxIdentity,InboundMailMessage
from stillpoint.signal_email import SignalEmailSafetyGate
from stillpoint.signal_mail import SignalMailPoller


class FakeIMAP:
    last=None
    search_result=b"10 41 55"
    raw_message=None
    def __init__(self,host,port,ssl_context=None,timeout=None):
        self.calls=[];FakeIMAP.last=self
    def login(self,user,password):self.calls.append(("login",user));return ("OK",[b"ok"])
    def select(self,box,readonly=False):self.calls.append(("select",box,readonly));return ("OK",[b"1"])
    def uid(self,command,*args):
        self.calls.append(("uid",command,args))
        if command=="search":return ("OK",[self.search_result])
        if command=="fetch":return ("OK",[(b"55 (BODY[] {1})",self.raw_message),b")"])
        raise AssertionError(command)
    def logout(self):self.calls.append(("logout",));return ("BYE",[b"bye"])


def message_with_auth(*auth_results, arc=(), received_spf=()):
    m=EmailMessage();m["From"]="Alice <alice@example.com>";m["To"]="owner@icloud.com";m["Subject"]="Meeting";m["Message-ID"]="<m1@example.com>"
    for value in auth_results:m["Authentication-Results"]=value
    for value in arc:m["ARC-Authentication-Results"]=value
    for value in received_spf:m["Received-SPF"]=value
    m.set_content("Could we meet Tuesday?")
    return m


class Patch039Tests(unittest.TestCase):
    def test_icloud_baseline_is_read_only_highest_uid_and_does_not_fetch_message(self):
        FakeIMAP.search_result=b"10 41 55"
        t=ICloudInboxTransport(account="owner@icloud.com",app_password="secret",jurisdiction="personal",imap_factory=FakeIMAP)
        self.assertEqual(t.baseline_cursor(),"55")
        self.assertIn(("select","INBOX",True),FakeIMAP.last.calls)
        self.assertIn(("uid","search",(None,"ALL")),FakeIMAP.last.calls)
        self.assertFalse(any(c[0]=="uid" and c[1]=="fetch" for c in FakeIMAP.last.calls))

    def test_icloud_fetch_without_explicit_cursor_fails_closed(self):
        t=ICloudInboxTransport(account="owner@icloud.com",app_password="secret",jurisdiction="personal",imap_factory=FakeIMAP)
        with self.assertRaisesRegex(Exception,"establish baseline first"):
            t.fetch_since(None)

    def test_fresh_generic_mailbox_baselines_without_creating_historical_work(self):
        con=sqlite3.connect(":memory:");con.row_factory=sqlite3.Row
        con.executescript('''
        create table trigger_definitions(trigger_id text primary key,owner_role text,trigger_kind text,source text,event_type text,status text);
        create table signal_email_decisions(decision_id text primary key,task_id text,event_id text,message_id text,account text,sender text,reply_target text,disposition text,classification text,requires_human integer,reason text,facts_json text,artifact_id text,action_id text,created_at text);
        insert into trigger_definitions values('ti','signal','event','icloud','message_received','active');
        ''')
        con.executescript((Path(__file__).resolve().parents[1]/"migrations"/"019_provider_neutral_mailboxes.sql").read_text())
        class DB:
            def _connection(self):return con
        class Triggers:
            events=[]
            def ingest_event(self,**kw):self.events.append(kw);raise AssertionError("historical mail must not be ingested on baseline")
            def fire_event(self,*a,**k):raise AssertionError("historical mail must not create tasks")
        class Transport:
            identity=MailboxIdentity("icloud","owner@icloud.com","personal")
            def baseline_cursor(self):return "114415"
            def fetch_since(self,*a,**k):raise AssertionError("fresh mailbox must baseline before fetch_since")
        out=SignalMailPoller(db=DB(),trigger_coordinator=Triggers(),transport=Transport(),trigger_id="ti").poll(now_iso="2026-09-17T20:00:00+00:00")
        self.assertEqual(out["status"],"baseline");self.assertEqual(out["cursor"],"114415");self.assertEqual(out["messages_seen"],0);self.assertEqual(out["tasks_created"],0)
        row=con.execute("select cursor from signal_mailboxes").fetchone();self.assertEqual(row["cursor"],"114415")
        receipt=con.execute("select status,messages_seen,tasks_created from signal_mail_poll_receipts").fetchone();self.assertEqual(tuple(receipt),("baseline",0,0))

    def test_missing_baseline_capability_fails_closed_without_fetching_backlog(self):
        con=sqlite3.connect(":memory:");con.row_factory=sqlite3.Row
        con.executescript('''
        create table trigger_definitions(trigger_id text primary key,owner_role text,trigger_kind text,source text,event_type text,status text);
        create table signal_email_decisions(decision_id text primary key,task_id text,event_id text,message_id text,account text,sender text,reply_target text,disposition text,classification text,requires_human integer,reason text,facts_json text,artifact_id text,action_id text,created_at text);
        insert into trigger_definitions values('ti','signal','event','icloud','message_received','active');
        ''')
        con.executescript((Path(__file__).resolve().parents[1]/"migrations"/"019_provider_neutral_mailboxes.sql").read_text())
        class DB:
            def _connection(self):return con
        class Triggers:pass
        class Transport:
            identity=MailboxIdentity("icloud","owner@icloud.com","personal")
            def fetch_since(self,*a,**k):raise AssertionError("unsafe backlog fetch attempted")
        with self.assertRaisesRegex(RuntimeError,"safe baseline_cursor"):
            SignalMailPoller(db=DB(),trigger_coordinator=Triggers(),transport=Transport(),trigger_id="ti").poll(now_iso="2026-09-17T20:00:00+00:00")
        row=con.execute("select cursor,last_error from signal_mailboxes").fetchone();self.assertIsNone(row["cursor"]);self.assertIn("baseline_cursor",row["last_error"])

    def test_icloud_preserves_chain_but_only_apple_receiver_auth_is_authoritative(self):
        msg=message_with_auth(
            "attacker.example; dmarc=pass; spf=pass; dkim=pass",
            "dkim-verifier.icloud.com; dkim=pass header.d=example.com",
            "spf.icloud.com; spf=pass smtp.mailfrom=example.com",
            "dmarc.icloud.com; dmarc=pass header.from=example.com",
            arc=("i=1; mx.example; dkim=pass; spf=pass; dmarc=pass",),
            received_spf=("pass (attacker supplied upstream evidence)",),
        )
        FakeIMAP.search_result=b"55";FakeIMAP.raw_message=msg.as_bytes()
        t=ICloudInboxTransport(account="owner@icloud.com",app_password="secret",jurisdiction="personal",imap_factory=FakeIMAP)
        messages,cursor=t.fetch_since("54")
        self.assertEqual(cursor,"55");m=messages[0]
        self.assertNotIn("attacker.example",m.authentication_results)
        self.assertIn("dkim-verifier.icloud.com",m.authentication_results);self.assertIn("spf.icloud.com",m.authentication_results);self.assertIn("dmarc.icloud.com",m.authentication_results)
        evidence=m.metadata["authentication_evidence"]
        self.assertTrue(any("attacker.example" in x for x in evidence["all_authentication_results"]))
        self.assertEqual(len(evidence["trusted_authentication_results"]),3)
        self.assertEqual(len(evidence["arc_authentication_results"]),1)
        self.assertEqual(len(evidence["received_spf"]),1)
        self.assertEqual(len(evidence["authentication_trace"]),6)
        self.assertTrue(all(item["receiver_side"] for item in evidence["authentication_trace"]))
        inbound={**m.to_event_payload(),"jurisdiction":"personal"}
        self.assertNotIn("sender_authentication_not_verified",SignalEmailSafetyGate().inbound_reasons(inbound))

    def test_non_icloud_forged_authentication_results_do_not_create_verified_sender(self):
        msg=message_with_auth("attacker.example; dmarc=pass; spf=pass; dkim=pass",received_spf=("pass",))
        FakeIMAP.search_result=b"55";FakeIMAP.raw_message=msg.as_bytes()
        t=ICloudInboxTransport(account="owner@icloud.com",app_password="secret",jurisdiction="personal",imap_factory=FakeIMAP)
        m=t.fetch_since("54")[0][0]
        self.assertEqual(m.authentication_results,"")
        self.assertIn("sender_authentication_not_verified",SignalEmailSafetyGate().inbound_reasons(m.to_event_payload()))

    def test_forged_icloud_authserv_id_below_receiver_received_boundary_is_not_trusted(self):
        msg=EmailMessage();msg["From"]="Mallory <mallory@evil.example>";msg["To"]="owner@icloud.com";msg["Subject"]="hello";msg["Message-ID"]="<m2@evil.example>"
        msg["Received"]="from evil.example by pv.example.icloud.com with ESMTP id x"
        msg["Authentication-Results"]="dmarc.icloud.com; dmarc=pass header.from=evil.example"
        msg.set_content("hello")
        FakeIMAP.search_result=b"56";FakeIMAP.raw_message=msg.as_bytes()
        t=ICloudInboxTransport(account="owner@icloud.com",app_password="secret",jurisdiction="personal",imap_factory=FakeIMAP)
        m=t.fetch_since("55")[0][0]
        self.assertEqual(m.authentication_results,"")
        self.assertTrue(any("dmarc.icloud.com" in x for x in m.metadata["authentication_evidence"]["all_authentication_results"]))
        self.assertIn("sender_authentication_not_verified",SignalEmailSafetyGate().inbound_reasons(m.to_event_payload()))

    def test_auth_gate_honors_dmarc_pass_even_if_one_underlying_method_fails(self):
        m={"from_address":"a@example.com","reply_to":"","cc":"","has_attachments":False,"text_plain_truncated":False,"authentication_results":"dmarc.icloud.com; dmarc=pass; spf.icloud.com; spf=fail; dkim-verifier.icloud.com; dkim=pass","subject":"hello","snippet":"hello","text_plain":"hello"}
        self.assertNotIn("sender_authentication_not_verified",SignalEmailSafetyGate().inbound_reasons(m))

    def test_dmarc_pass_remains_authoritative_with_multiple_dkim_signature_results(self):
        m={"from_address":"a@example.com","reply_to":"","cc":"","has_attachments":False,"text_plain_truncated":False,"authentication_results":"dmarc.icloud.com; dmarc=pass; dkim-verifier.icloud.com; dkim=pass; dkim=fail","subject":"hello","snippet":"hello","text_plain":"hello"}
        self.assertNotIn("sender_authentication_not_verified",SignalEmailSafetyGate().inbound_reasons(m))

    def test_auth_gate_rejects_conflicting_duplicate_method_results(self):
        m={"from_address":"a@example.com","reply_to":"","cc":"","has_attachments":False,"text_plain_truncated":False,"authentication_results":"dmarc.icloud.com; dmarc=pass; dmarc.icloud.com; dmarc=fail","subject":"hello","snippet":"hello","text_plain":"hello"}
        self.assertIn("sender_authentication_not_verified",SignalEmailSafetyGate().inbound_reasons(m))

    def test_auth_gate_accepts_spf_and_dkim_pass_without_dmarc(self):
        m={"from_address":"a@example.com","reply_to":"","cc":"","has_attachments":False,"text_plain_truncated":False,"authentication_results":"spf.icloud.com; spf=pass; dkim-verifier.icloud.com; dkim=pass","subject":"hello","snippet":"hello","text_plain":"hello"}
        self.assertNotIn("sender_authentication_not_verified",SignalEmailSafetyGate().inbound_reasons(m))

if __name__=="__main__":unittest.main()
