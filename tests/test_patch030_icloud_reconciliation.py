from __future__ import annotations
import hashlib,unittest
from email.message import EmailMessage
from stillpoint.adapters.icloud_mail import ICloudSendAdapter
from stillpoint.mail_reconciliation import reconcile_mail_send
from stillpoint.contracts.models import ActionRequest,ArtifactRef

class DB:
    def __init__(self):
        self.body='Hello';self.sha=hashlib.sha256(self.body.encode()).hexdigest()
    def get_artifact(self,aid):return {'id':aid,'task_id':'t1','version':1,'sha256':self.sha,'produced_by_run_id':'r1'}
    def get_run(self,rid):return {'output':self.body}

class SentIMAP:
    mode='exact';last=None
    def __init__(self,*a,**k):self.calls=[];SentIMAP.last=self
    def login(self,*a):return ('OK',[b'ok'])
    def list(self):return ('OK',[b'(\\HasNoChildren \\Sent) "/" "Sent Messages"'])
    def select(self,folder,readonly=False):self.calls.append(('select',folder,readonly));return ('OK',[b'1'])
    def uid(self,cmd,*args):
        self.calls.append((cmd,args))
        if cmd=='search':
            if self.mode=='zero':return ('OK',[b''])
            if self.mode=='many':return ('OK',[b'7 8'])
            return ('OK',[b'7'])
        if cmd=='fetch':
            m=EmailMessage();m['Message-ID']='<stillpoint-a1@stillpoint.invalid>';m['From']='owner@icloud.com';m['To']='alice@example.com';m['Subject']='Re: Meeting'
            if self.mode=='mismatch':m.replace_header('To','other@example.com')
            return ('OK',[(b'7',m.as_bytes()),b')'])
        raise AssertionError(cmd)
    def logout(self):return ('BYE',[b'bye'])

class Patch030Tests(unittest.TestCase):
    def req(self):
        db=DB();ref=ArtifactRef(name='x',sha256=db.sha,kind='email',artifact_id='art1',version=1)
        req=ActionRequest(action_id='a1',task_id='t1',action_type='send_email',target='from owner@icloud.com to alice@example.com subject: Re: Meeting',scope=['from owner@icloud.com to alice@example.com subject: Re: Meeting'],artifact_refs=[ref],approval_required=False,approval_id=None,expires_at='2099-01-01T00:00:00+00:00',issued_at='2026-01-01T00:00:00+00:00',idempotency_key='i',success_criteria=['provider_acceptance_receipt'],authority_revision='r',warrant_id='w1')
        return db,req
    def adapter(self,mode='exact'):
        SentIMAP.mode=mode;db,req=self.req();return ICloudSendAdapter(db=db,account='owner@icloud.com',app_password='secret',jurisdiction='personal',enabled=True,imap_factory=SentIMAP),req
    def test_exact_sent_message_confirms_effect(self):
        a,r=self.adapter();p=a.probe_existing(r);self.assertTrue(p['effect_occurred']);self.assertEqual(p['matches'],['7']);self.assertIn(('select','Sent Messages',True),SentIMAP.last.calls)
    def test_zero_matches_remains_ambiguous(self):
        a,r=self.adapter('zero');p=a.probe_existing(r);self.assertIsNone(p['effect_occurred'])
    def test_multiple_matches_remain_ambiguous(self):
        a,r=self.adapter('many');p=a.probe_existing(r);self.assertIsNone(p['effect_occurred'])
    def test_header_mismatch_remains_ambiguous(self):
        a,r=self.adapter('mismatch');p=a.probe_existing(r);self.assertIsNone(p['effect_occurred'])
    def test_provider_neutral_reconcile_only_confirms_true_effect(self):
        class RDB:
            def get_action_request(self,a):return {'id':a}
            def get_action_dispatch(self,a):return {'state':'uncertain','adapter':'icloud_send'}
        class RT:
            db=RDB()
            def _request_from_row(self,row):return object()
            def reconcile_action_dispatch(self,*a,**k):return {'state':'reconciled_effect'}
        class A:
            name='icloud_send'
            def probe_existing(self,r):return {'effect_occurred':True,'evidence':[],'note':'exact','matches':['7']}
        out=reconcile_mail_send(RT(),'a1',A());self.assertEqual(out['status'],'reconciled_effect')
    def test_ambiguous_probe_never_reauthorizes_retry(self):
        class RDB:
            def get_action_request(self,a):return {'id':a}
            def get_action_dispatch(self,a):return {'state':'uncertain','adapter':'icloud_send'}
        class RT:
            db=RDB()
            def _request_from_row(self,row):return object()
            def reconcile_action_dispatch(self,*a,**k):raise AssertionError('must not reconcile ambiguous as no effect')
        class A:
            name='icloud_send'
            def probe_existing(self,r):return {'effect_occurred':None,'evidence':[],'note':'zero matches','matches':[]}
        out=reconcile_mail_send(RT(),'a1',A());self.assertEqual(out['status'],'ambiguous')
if __name__=='__main__':unittest.main()
