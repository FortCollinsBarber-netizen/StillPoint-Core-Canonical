import json,sqlite3,tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from stillpoint.signal_governance import SignalGovernanceSpec,SCHEMA,CEO_ISSUER
from stillpoint.signal_service import SignalServiceConfig
from stillpoint.signal_release_gate import SignalReleaseGate
NOW=datetime(2026,9,17,22,0,tzinfo=timezone.utc)
def iso(d):return d.isoformat()
def raw():return {'schema':SCHEMA,'issuer':CEO_ISSUER,'spec_id':'s','gmail_account':'signal@example.com','delegation_id':'del','trigger_id':'trig','policy_basis':'p','purpose':'p','claim_envelope_ids':['env'],'allowed_classifications':['scheduling'],'continuation_conditions':[{'key':'company_policy_current','operator':'eq','expected':True}],'additional_execution_conditions':[],'exclusions':['money'],'release_conditions':['review'],'valid_from':iso(NOW-timedelta(minutes=1)),'review_by':iso(NOW+timedelta(days=1)),'trigger_valid_from':iso(NOW-timedelta(minutes=1)),'trigger_review_by':iso(NOW+timedelta(days=1)),'facts_snapshot':{'observed_at':iso(NOW-timedelta(minutes=1)),'valid_until':iso(NOW+timedelta(hours=1)),'facts':{'company_policy_current':True}}}
class DB:
 def __init__(self,spec):
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row;d=spec.digest();self.c.executescript('''
CREATE TABLE standing_delegations(delegation_id TEXT PRIMARY KEY,policy_basis TEXT,status TEXT);
CREATE TABLE trigger_definitions(trigger_id TEXT PRIMARY KEY,metadata_json TEXT,status TEXT);
CREATE TABLE temporal_claim_envelopes(envelope_id TEXT PRIMARY KEY,status TEXT);
CREATE TABLE signal_email_decisions(action_id TEXT,account TEXT);
CREATE TABLE action_dispatches(action_id TEXT PRIMARY KEY,state TEXT);
CREATE TABLE action_requests(id TEXT PRIMARY KEY,authorization_mode TEXT,standing_delegation_id TEXT,standing_evaluation_id TEXT,warrant_id TEXT);
''');self.c.execute('insert into standing_delegations values(?,?,?)',('del','x;signal_governance_spec:'+d,'active'));self.c.execute('insert into trigger_definitions values(?,?,?)',('trig',json.dumps({'signal_governance_sha256':d}),'active'));self.c.execute("insert into temporal_claim_envelopes values('env','active')");self.c.commit()
 def _connection(self):return self.c
class Tests(unittest.TestCase):
 def setUp(self):
  self.td=tempfile.TemporaryDirectory();root=Path(self.td.name);f=root/'facts.json';f.write_text('{}');self.cfg=SignalServiceConfig(root=root,provider_name='xai',model='m',gmail_account='signal@example.com',gmail_access_token='s',delegation_id='del',trigger_id='trig',facts_file=f,worker_id='w');self.spec=SignalGovernanceSpec.from_dict(raw());self.db=DB(self.spec);self.validator=lambda cfg:{'ready':True}
 def tearDown(self):self.td.cleanup()
 def gate(self):return SignalReleaseGate(db=self.db,config=self.cfg,governance_spec=self.spec,validator=self.validator).run()
 def test_all_exact_bindings_pass(self):self.assertEqual(self.gate().verdict,'PASS')
 def test_delegation_digest_mismatch_halts(self):self.db.c.execute("update standing_delegations set policy_basis='other'");self.db.c.commit();r=self.gate();self.assertEqual(r.verdict,'HALT');self.assertFalse([x for x in r.checks if x.name=='delegation_digest'][0].ok)
 def test_former_supporting_envelope_halts(self):self.db.c.execute("update temporal_claim_envelopes set status='historical'");self.db.c.commit();self.assertEqual(self.gate().verdict,'HALT')
 def test_uncertain_external_effect_halts(self):self.db.c.execute("insert into signal_email_decisions values('a','signal@example.com')");self.db.c.execute("insert into action_dispatches values('a','uncertain')");self.db.c.commit();self.assertEqual(self.gate().verdict,'HALT')
 def test_incomplete_delegated_lineage_halts(self):self.db.c.execute("insert into signal_email_decisions values('a','signal@example.com')");self.db.c.execute("insert into action_requests values('a','standing_delegation','del',NULL,NULL)");self.db.c.commit();self.assertEqual(self.gate().verdict,'HALT')
 def test_service_readiness_failure_halts(self):self.validator=lambda cfg:{'ready':False};self.assertEqual(self.gate().verdict,'HALT')
if __name__=='__main__':unittest.main()
