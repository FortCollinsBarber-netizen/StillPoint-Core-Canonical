from __future__ import annotations
import json,re,unittest
from email.message import EmailMessage
from pathlib import Path

from stillpoint.adapters.icloud_mail import ICloudInboxTransport
from stillpoint.signal_email import SignalEmailSafetyGate
from tests.test_patch039_production_intake_integrity import FakeIMAP

ROOT=Path(__file__).resolve().parents[1]


def _fetch(msg, uid='90'):
    FakeIMAP.search_result=uid.encode('ascii');FakeIMAP.raw_message=msg.as_bytes()
    t=ICloudInboxTransport(account='owner@icloud.com',app_password='secret',jurisdiction='personal',imap_factory=FakeIMAP)
    return t.fetch_since(str(int(uid)-1))[0][0]


def _base(sender='Alice <alice@example.com>', subject='hello'):
    m=EmailMessage();m['Return-Path']='<alice@example.com>'
    m['Received']='from p00-icloudmta-smtpin-us-central-1n-100-percent-11 by p121-mailgateway-smtp-664cf66f65-test with SMTP id outer'
    m['Received']='from mail.example.com by p00-icloudmta-smtpin-us-central-1n-100-percent-11 with ESMTPS id border'
    m['From']=sender;m['To']='owner@icloud.com';m['Subject']=subject;m['Message-ID']='<patch041@example.com>'
    return m


class Patch041Tests(unittest.TestCase):
    def test_real_icloud_delivery_order_trusts_apple_results_after_received(self):
        m=_base('Robert Holmes <rholmes4@students.ccu.edu>','StillPoint live proof')
        m['Authentication-Results']='bimi.icloud.com; bimi=skipped reason="insufficient dmarc"'
        m['Authentication-Results']='arc.icloud.com; arc=pass'
        m['Authentication-Results']='dmarc.icloud.com; dmarc=pass header.from=students.ccu.edu'
        m['Authentication-Results']='dkim-verifier.icloud.com; dkim=pass header.d=students-ccu-edu.20251104.gappssmtp.com'
        m['Received-SPF']='pass (spf.icloud.com: permitted sender) receiver=spf.icloud.com; envelope-from=rholmes4@students.ccu.edu'
        m['Authentication-Results']='spf.icloud.com; spf=pass smtp.mailfrom=rholmes4@students.ccu.edu'
        m['Received']='by mail.example.com with SMTP id upstream'
        m.set_content('Please acknowledge receipt of this message.')
        got=_fetch(m)
        self.assertIn('dmarc.icloud.com; dmarc=pass',got.authentication_results)
        self.assertIn('dkim-verifier.icloud.com; dkim=pass',got.authentication_results)
        self.assertIn('spf.icloud.com; spf=pass',got.authentication_results)
        self.assertNotIn('bimi.icloud.com',got.authentication_results)
        self.assertNotIn('sender_authentication_not_verified',SignalEmailSafetyGate().inbound_reasons(got.to_event_payload()))
        evidence=got.metadata['authentication_evidence']
        trusted=evidence['trusted_authentication_results']
        services={item.split(';',1)[0].strip().lower() for item in trusted}
        self.assertEqual(services,{'dmarc.icloud.com','dkim-verifier.icloud.com','spf.icloud.com'})
        self.assertNotIn('arc.icloud.com',services)
        self.assertNotIn('bimi.icloud.com',services)
        self.assertEqual(len(trusted),3)
        self.assertTrue(any(item['received_headers_before']>=2 and item['trusted_icloud_authserv_id'] for item in evidence['authentication_trace']))

    def test_zillow_shape_authenticates_but_reply_to_boundary_still_blocks(self):
        m=_base('Zillow <zmail@zmail.zillow.com>','Have you done any home updates?')
        m['Reply-To']='no-reply@mail.zillow.com'
        m['Authentication-Results']='dmarc.icloud.com; dmarc=pass header.from=zmail.zillow.com'
        m['Authentication-Results']='dkim-verifier.icloud.com; dkim=pass header.d=zmail.zillow.com'
        m['Authentication-Results']='spf.icloud.com; spf=pass smtp.mailfrom=amazonses.com'
        m.set_content('Automated marketing message')
        got=_fetch(m,'91')
        reasons=SignalEmailSafetyGate().inbound_reasons(got.to_event_payload())
        self.assertNotIn('sender_authentication_not_verified',reasons)
        self.assertIn('reply_to_differs_from_sender',reasons)

    def test_non_apple_authserv_ids_remain_audit_only(self):
        m=_base()
        m['Authentication-Results']='attacker.example; dmarc=pass; dkim=pass; spf=pass'
        m.set_content('hello')
        got=_fetch(m,'92')
        self.assertEqual(got.authentication_results,'')
        evidence=got.metadata['authentication_evidence']
        self.assertTrue(any('attacker.example' in x for x in evidence['all_authentication_results']))
        self.assertIn('sender_authentication_not_verified',SignalEmailSafetyGate().inbound_reasons(got.to_event_payload()))

    def test_conflicting_exact_apple_results_fail_closed(self):
        m=_base()
        m['Authentication-Results']='dmarc.icloud.com; dmarc=pass header.from=example.com'
        m['Authentication-Results']='dmarc.icloud.com; dmarc=fail header.from=example.com'
        m.set_content('hello')
        got=_fetch(m,'93')
        self.assertIn('sender_authentication_not_verified',SignalEmailSafetyGate().inbound_reasons(got.to_event_payload()))

    def test_trusted_service_must_report_its_expected_method(self):
        m=_base()
        m['Authentication-Results']='dmarc.icloud.com; spf=pass smtp.mailfrom=example.com'
        m.set_content('hello')
        got=_fetch(m,'94')
        self.assertEqual(got.authentication_results,'')
        self.assertIn('sender_authentication_not_verified',SignalEmailSafetyGate().inbound_reasons(got.to_event_payload()))

    def test_release_identity_tracks_patch041_and_patch040_provenance(self):
        cp=json.loads((ROOT/'CHECKPOINT.json').read_text())
        mf=json.loads((ROOT/'RELEASE_MANIFEST.json').read_text())
        self.assertEqual(cp['last_completed_milestone'],'patch-041-icloud-auth-boundary-correction')
        self.assertEqual(cp['release_candidate']['closure_patch'],'041')
        self.assertEqual(mf['patch'],'041-icloud-auth-boundary-correction')
        expected='8c06cf9079b05083b46cf9c9982d580b2be8148f'
        self.assertEqual(cp['git']['patch040_merge_commit'],expected)
        self.assertEqual(mf['provenance']['canonical_patch040_merge'],expected)

if __name__=='__main__':unittest.main()
