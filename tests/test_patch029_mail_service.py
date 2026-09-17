from __future__ import annotations
import tempfile,unittest
from pathlib import Path
from stillpoint.signal_mail_service import SignalMailboxServiceConfig,SignalServiceConfigurationError,validate_mailbox_delegation
from stillpoint.mail_contracts import MailboxIdentity
from stillpoint.signal_mail_governance import MailboxGovernanceSpec
from stillpoint.temporal.envelope import ContinuationCondition,ConditionOperator

class Patch029Tests(unittest.TestCase):
    def _facts(self):
        p=Path(tempfile.mkdtemp())/'facts.json';p.write_text('{}');return p
    def _env(self,provider='icloud'):
        facts=self._facts();e={'STILLPOINT_ROOT':str(facts.parent),'STILLPOINT_MAIL_PROVIDER':provider,'STILLPOINT_MAIL_ACCOUNT':'owner@icloud.com' if provider=='icloud' else 'student@example.com','STILLPOINT_MAIL_JURISDICTION':'personal' if provider=='icloud' else 'school','STILLPOINT_SIGNAL_DELEGATION_ID':'d1','STILLPOINT_SIGNAL_MAIL_TRIGGER_ID':'t1','STILLPOINT_SIGNAL_GOVERNANCE_SHA256':'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','STILLPOINT_SIGNAL_FACTS_FILE':str(facts),'STILLPOINT_PROVIDER':'mock','STILLPOINT_SIGNAL_ALLOW_MOCK':'1'}
        if provider=='icloud':e['STILLPOINT_ICLOUD_APP_PASSWORD']='app-secret'
        else:e['STILLPOINT_GMAIL_ACCESS_TOKEN']='oauth-token'
        return e
    def _standing(self,identity):
        return MailboxGovernanceSpec(identity=identity,delegation_id='d1',claim_envelope_ids=['e1'],allowed_classifications=['scheduling'],continuation_conditions=[ContinuationCondition('policy.current',ConditionOperator.EQ,True)],exclusions=['money'],release_conditions=['review'],valid_from='2026-09-01T00:00:00+00:00',review_by='2026-10-17T00:00:00+00:00',policy_basis='p',purpose='routine').standing()
    def test_icloud_config_uses_app_specific_secret_and_redacts_it(self):
        c=SignalMailboxServiceConfig.from_env(self._env('icloud'));self.assertEqual(c.identity.provider,'icloud');self.assertEqual(c.credential,'app-secret');self.assertNotIn('app-secret',str(c.redacted()))
    def test_gmail_config_remains_supported_for_school(self):
        c=SignalMailboxServiceConfig.from_env(self._env('gmail'));self.assertEqual(c.identity.jurisdiction,'school');self.assertEqual(c.credential,'oauth-token')
    def test_missing_icloud_secret_fails_closed(self):
        e=self._env('icloud');e.pop('STILLPOINT_ICLOUD_APP_PASSWORD')
        with self.assertRaises(SignalServiceConfigurationError):SignalMailboxServiceConfig.from_env(e)
    def test_delegation_must_bind_exact_three_part_identity(self):
        i=MailboxIdentity('icloud','owner@icloud.com','personal');d=self._standing(i)
        self.assertIs(validate_mailbox_delegation(d,i,now_iso='2026-09-17T12:00:00+00:00'),d)
        with self.assertRaises(SignalServiceConfigurationError):validate_mailbox_delegation(d,MailboxIdentity('icloud','owner@icloud.com','barber'),now_iso='2026-09-17T12:00:00+00:00')
    def test_delegation_review_boundary_stops_service(self):
        i=MailboxIdentity('icloud','owner@icloud.com','personal');d=self._standing(i)
        with self.assertRaises(SignalServiceConfigurationError):validate_mailbox_delegation(d,i,now_iso='2026-10-17T00:00:00+00:00')
    def test_worker_identity_includes_provider_and_jurisdiction(self):
        c=SignalMailboxServiceConfig.from_env(self._env('icloud'));self.assertIn('icloud',c.worker_id);self.assertIn('personal',c.worker_id)
if __name__=='__main__':unittest.main()
