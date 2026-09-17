import json,sqlite3,tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from stillpoint.signal_governance import SignalGovernanceSpec,SignalGovernanceProvisioner,SignalGovernanceError,SCHEMA,CEO_ISSUER
NOW=datetime(2026,9,17,22,0,tzinfo=timezone.utc)
def iso(d):return d.isoformat()
def spec_raw():
 return {'schema':SCHEMA,'issuer':CEO_ISSUER,'spec_id':'sig-pol-1','gmail_account':'signal@example.com','delegation_id':'del-1','trigger_id':'trig-1','policy_basis':'CEO approved Signal routine email','purpose':'Routine business email','claim_envelope_ids':['env-1'],'allowed_classifications':['scheduling','acknowledgement'],'continuation_conditions':[{'key':'company_policy_current','operator':'eq','expected':True}], 'additional_execution_conditions':[],'exclusions':['money','contracts','legal','security'],'release_conditions':['CEO revocation','review boundary','supporting envelope no longer current'],'valid_from':iso(NOW-timedelta(minutes=1)),'review_by':iso(NOW+timedelta(days=7)),'trigger_valid_from':iso(NOW-timedelta(minutes=1)),'trigger_review_by':iso(NOW+timedelta(days=7)),'facts_snapshot':{'observed_at':iso(NOW-timedelta(minutes=1)),'valid_until':iso(NOW+timedelta(hours=1)),'source':'CEO','facts':{'company_policy_current':True},'envelopes':{'env-1':{'policy_current':True}}}}
class DB:
 def __init__(self):
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row;self.c.executescript('''
CREATE TABLE temporal_claim_envelopes(envelope_id TEXT PRIMARY KEY,status TEXT);
CREATE TABLE standing_delegations(delegation_id TEXT PRIMARY KEY,delegate_role TEXT,issuer TEXT,policy_basis TEXT,purpose TEXT,claim_envelope_ids_json TEXT,allowed_action_types_json TEXT,continuation_conditions_json TEXT,execution_conditions_json TEXT,exclusions_json TEXT,release_conditions_json TEXT,valid_from TEXT,review_by TEXT,status TEXT,supersedes_delegation_id TEXT,created_at TEXT,updated_at TEXT);
CREATE TABLE trigger_definitions(trigger_id TEXT PRIMARY KEY,owner_role TEXT,trigger_kind TEXT,source TEXT,event_type TEXT,goal_template TEXT,project TEXT,status TEXT,valid_from TEXT,review_by TEXT,next_run_at TEXT,interval_seconds INTEGER,max_runs INTEGER,run_count INTEGER,catch_up_policy TEXT,metadata_json TEXT,created_at TEXT,updated_at TEXT);
''');self.c.execute("insert into temporal_claim_envelopes values('env-1','active')");self.c.commit()
 def _connection(self):return self.c
class Tests(unittest.TestCase):
 def setUp(self):self.db=DB();self.p=SignalGovernanceProvisioner(self.db);self.spec=SignalGovernanceSpec.from_dict(spec_raw())
 def test_digest_is_deterministic(self):
  self.assertEqual(self.spec.digest(),SignalGovernanceSpec.from_dict(spec_raw()).digest());self.assertEqual(len(self.spec.digest()),64)
 def test_unsafe_classification_cannot_enter_autonomy_allowset(self):
  r=spec_raw();r['allowed_classifications']=['sensitive']
  with self.assertRaises(SignalGovernanceError):SignalGovernanceSpec.from_dict(r)
 def test_machine_execution_conditions_are_derived(self):
  c={x.key:(x.operator.value,x.expected) for x in self.spec.execution_conditions()};self.assertEqual(c['signal_email.account'],('eq','signal@example.com'));self.assertEqual(c['signal_email.requires_human'],('eq',False));self.assertEqual(c['signal_email.classification'][0],'in')
 def test_preview_is_read_only_and_ready(self):
  before=self.db.c.total_changes;out=self.p.preview(self.spec);after=self.db.c.total_changes;self.assertTrue(out['ready_to_apply']);self.assertEqual(before,after)
 def test_missing_or_former_envelope_blocks_preview(self):
  self.db.c.execute("update temporal_claim_envelopes set status='historical'");self.db.c.commit();out=self.p.preview(self.spec);self.assertFalse(out['ready_to_apply']);self.assertEqual(out['noncurrent_envelopes'],['env-1'])
 def test_apply_requires_explicit_ceo_and_exact_digest(self):
  with tempfile.TemporaryDirectory() as td:
   f=Path(td)/'facts.json'
   with self.assertRaises(SignalGovernanceError):self.p.apply(self.spec,facts_file=f,expected_sha256=self.spec.digest(),ceo_confirmed=False)
   with self.assertRaises(SignalGovernanceError):self.p.apply(self.spec,facts_file=f,expected_sha256='0'*64,ceo_confirmed=True)
 def test_apply_persists_bounded_delegation_trigger_and_facts(self):
  with tempfile.TemporaryDirectory() as td:
   f=Path(td)/'facts.json';out=self.p.apply(self.spec,facts_file=f,expected_sha256=self.spec.digest(),ceo_confirmed=True);self.assertTrue(out['applied']);d=self.db.c.execute('select * from standing_delegations').fetchone();t=self.db.c.execute('select * from trigger_definitions').fetchone();self.assertEqual(d['delegate_role'],'signal');self.assertIn('signal_governance_spec:'+self.spec.digest(),d['policy_basis']);self.assertEqual(t['source'],'gmail');self.assertEqual(t['event_type'],'message_received');self.assertTrue(f.is_file());self.assertEqual(json.loads(f.read_text())['facts']['company_policy_current'],True)
 def test_same_policy_is_idempotent_but_conflicting_ids_fail(self):
  with tempfile.TemporaryDirectory() as td:
   f=Path(td)/'facts.json';self.p.apply(self.spec,facts_file=f,expected_sha256=self.spec.digest(),ceo_confirmed=True);out=self.p.apply(self.spec,facts_file=f,expected_sha256=self.spec.digest(),ceo_confirmed=True);self.assertTrue(out['reused_existing']);r=spec_raw();r['purpose']='different';other=SignalGovernanceSpec.from_dict(r);preview=self.p.preview(other);self.assertFalse(preview['ready_to_apply']);self.assertTrue(preview['conflicts'])
if __name__=='__main__':unittest.main()
