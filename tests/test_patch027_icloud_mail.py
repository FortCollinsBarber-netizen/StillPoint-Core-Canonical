from __future__ import annotations
import hashlib
import unittest
from dataclasses import dataclass
from email.message import EmailMessage

from stillpoint.mail_contracts import MailboxIdentity
from stillpoint.adapters.mail_common import MailBoundaryError, parse_authorized_send_target
from stillpoint.adapters.icloud_mail import (
    ICloudInboxTransport,ICloudMailBoundaryError,ICloudSendAdapter,IMAP_HOST,IMAP_PORT,SMTP_HOST,SMTP_PORT
)
from stillpoint.contracts.models import ActionRequest,ArtifactRef

class FakeDB:
    def __init__(self, body='Hello from StillPoint'):
        self.body=body
        self.sha=hashlib.sha256(body.encode()).hexdigest()
    def get_artifact(self, aid):
        return {'id':aid,'task_id':'task1','version':1,'sha256':self.sha,'produced_by_run_id':'run1'}
    def get_run(self, rid):
        return {'id':rid,'output':self.body}

class FakeSMTP:
    last=None
    def __init__(self,host,port,timeout=None):
        self.host=host;self.port=port;self.timeout=timeout;self.calls=[];FakeSMTP.last=self
    def ehlo(self):self.calls.append(('ehlo',));return (250,b'ok')
    def starttls(self,context=None):self.calls.append(('starttls',bool(context)));return (220,b'ok')
    def login(self,user,password):self.calls.append(('login',user,password));return (235,b'ok')
    def send_message(self,msg,from_addr=None,to_addrs=None):
        self.calls.append(('send',from_addr,tuple(to_addrs or []),msg['Message-ID']));return {}
    def quit(self):self.calls.append(('quit',));return (221,b'bye')

class FakeIMAP:
    last=None
    def __init__(self,host,port,ssl_context=None,timeout=None):
        self.host=host;self.port=port;self.timeout=timeout;self.calls=[];FakeIMAP.last=self
        m=EmailMessage();m['From']='Alice <alice@example.com>';m['To']='owner@icloud.com';m['Subject']='Meeting';m['Message-ID']='<m1@example.com>';m['Authentication-Results']='dmarc.icloud.com; dmarc=pass header.from=example.com';m['Authentication-Results']='dkim-verifier.icloud.com; dkim=pass header.d=example.com';m['Authentication-Results']='spf.icloud.com; spf=pass smtp.mailfrom=example.com';m.set_content('Could we meet Tuesday?')
        self.raw=m.as_bytes()
    def login(self,user,password):self.calls.append(('login',user,password));return ('OK',[b'ok'])
    def select(self,box,readonly=False):self.calls.append(('select',box,readonly));return ('OK',[b'1'])
    def uid(self,command,*args):
        self.calls.append(('uid',command,args))
        if command=='search':return ('OK',[b'41'])
        if command=='fetch':return ('OK',[(b'41 (BODY[] {1})',self.raw),b')'])
        raise AssertionError(command)
    def logout(self):self.calls.append(('logout',));return ('BYE',[b'bye'])

class Patch027Tests(unittest.TestCase):
    def _request(self,db,**kw):
        ref=ArtifactRef(name='reply.txt',sha256=db.sha,kind='email',artifact_id='art1',version=1)
        base=dict(action_id='a1',task_id='task1',action_type='send_email',target='from owner@icloud.com to alice@example.com subject: Re: Meeting',scope=['from owner@icloud.com to alice@example.com subject: Re: Meeting'],artifact_refs=[ref],approval_required=False,approval_id=None,expires_at='2099-01-01T00:00:00+00:00',issued_at='2026-01-01T00:00:00+00:00',idempotency_key='idem',success_criteria=['provider_acceptance_receipt'],authority_revision='r1',warrant_id='w1')
        base.update(kw);return ActionRequest(**base)

    def test_mailbox_identity_is_provider_account_jurisdiction(self):
        i=MailboxIdentity('iCloud','Owner@icloud.com','Personal')
        self.assertEqual(i.authority_subject,'mailbox:icloud:owner@icloud.com:personal')
        self.assertNotEqual(i,MailboxIdentity('icloud','owner@icloud.com','fort_collins_barber'))

    def test_common_target_parser_is_provider_neutral_and_bounded(self):
        self.assertEqual(parse_authorized_send_target('from owner@icloud.com to a@example.com subject: Hi'),('owner@icloud.com','a@example.com','Hi'))
        with self.assertRaises(MailBoundaryError):parse_authorized_send_target('from owner@icloud.com to a@example.com cc: b@example.com subject: Hi')

    def test_icloud_send_requires_runtime_secret_when_enabled(self):
        with self.assertRaises(ICloudMailBoundaryError):ICloudSendAdapter(db=FakeDB(),account='owner@icloud.com',app_password='',jurisdiction='personal',enabled=True,smtp_factory=FakeSMTP)

    def test_icloud_send_uses_starttls_and_exact_account(self):
        db=FakeDB();req=self._request(db)
        a=ICloudSendAdapter(db=db,account='owner@icloud.com',app_password='app-specific-secret',jurisdiction='personal',enabled=True,smtp_factory=FakeSMTP)
        result=a.execute(req)
        self.assertEqual(result.status,'succeeded');self.assertEqual(result.adapter,'icloud_send')
        self.assertEqual(FakeSMTP.last.host,SMTP_HOST);self.assertEqual(FakeSMTP.last.port,SMTP_PORT)
        self.assertIn(('login','owner@icloud.com','app-specific-secret'),FakeSMTP.last.calls)
        self.assertTrue(any(c[0]=='starttls' for c in FakeSMTP.last.calls))
        self.assertEqual(result.evidence[0].satisfies,'provider_acceptance_receipt')
        self.assertIn('provider_acceptance_not_recipient_read_or_final_delivery',result.evidence[0].note)

    def test_icloud_send_rejects_sender_jurisdiction_mismatch(self):
        db=FakeDB();req=self._request(db,target='from other@icloud.com to alice@example.com subject: Hi',scope=['from other@icloud.com to alice@example.com subject: Hi'])
        a=ICloudSendAdapter(db=db,account='owner@icloud.com',app_password='secret',jurisdiction='personal',enabled=True,smtp_factory=FakeSMTP)
        self.assertFalse(a.can_execute(req))
        with self.assertRaises(ICloudMailBoundaryError):a.execute(req)

    def test_icloud_inbox_is_read_only_and_normalizes_message(self):
        t=ICloudInboxTransport(account='owner@icloud.com',app_password='secret',jurisdiction='personal',imap_factory=FakeIMAP)
        messages,cursor=t.fetch_since('40')
        self.assertEqual(cursor,'41');self.assertEqual(len(messages),1)
        m=messages[0]
        self.assertEqual(m.provider,'icloud');self.assertEqual(m.account,'owner@icloud.com');self.assertEqual(m.from_address,'alice@example.com')
        self.assertEqual(m.text_plain,'Could we meet Tuesday?')
        self.assertIn('dmarc=pass',m.authentication_results)
        self.assertIn(('select','INBOX',True),FakeIMAP.last.calls)
        self.assertEqual(FakeIMAP.last.host,IMAP_HOST);self.assertEqual(FakeIMAP.last.port,IMAP_PORT)

    def test_inbox_cursor_is_monotonic_uid(self):
        t=ICloudInboxTransport(account='owner@icloud.com',app_password='secret',jurisdiction='barber',imap_factory=FakeIMAP)
        _,cursor=t.fetch_since('40')
        search=[c for c in FakeIMAP.last.calls if c[0]=='uid' and c[1]=='search'][0]
        self.assertIn('UID 41:*',search[2]);self.assertEqual(cursor,'41')

if __name__=='__main__':unittest.main()
