import json,sqlite3,unittest
from datetime import datetime,timedelta,timezone
from stillpoint.signal_governance import CEO_ISSUER
from stillpoint.signal_governance_bootstrap import DRAFT_SCHEMA,build_plan,SignalGovernanceBootstrapper,SignalGovernanceError
NOW=datetime(2026,9,17,18,0,tzinfo=timezone.utc)
def iso(x): return x.isoformat()
def raw():
 return {'schema':DRAFT_SCHEMA,'issuer':CEO_ISSUER,'spec_id':'sig-pol-1','gmail_account':'signal@example.com','delegation_id':'del-1','trigger_id':'trig-1','policy_basis':'CEO Signal routine email','purpose':'Routine business email','allowed_classifications':['scheduling','acknowledgement'],'continuation_conditions':[{'key':'signal_governance.policy_current','operator':'eq','expected':True}],'additional_execution_conditions':[],'exclusions':['money','contracts','legal','security','medical'],'release_conditions':['CEO revocation','review boundary','supporting envelope no longer current'],'valid_from':iso(NOW),'review_by':iso(NOW+timedelta(days=30)),'trigger_valid_from':iso(NOW),'trigger_review_by':iso(NOW+timedelta(days=30)),'facts_snapshot':{'observed_at':iso(NOW),'valid_until':iso(NOW+timedelta(hours=8)),'source':'CEO','facts':{'signal_email':{'account':'signal@example.com'},'signal_governance':{'spec_id':'sig-pol-1','policy_current':True}}}}
class DB:
 def __init__(self):
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row;self.c.executescript('''
CREATE TABLE temporal_claims(claim_id TEXT PRIMARY KEY,subject TEXT NOT NULL,predicate TEXT NOT NULL,value_json TEXT,domain TEXT NOT NULL,source TEXT NOT NULL,evidence_refs_json TEXT NOT NULL DEFAULT '[]',time_observed TEXT,time_asserted TEXT NOT NULL,effective_from TEXT,effective_to TEXT,confidence REAL,status TEXT NOT NULL,supersedes TEXT,superseded_by TEXT,review_conditions_json TEXT NOT NULL DEFAULT '[]',provenance_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE temporal_claim_envelopes(envelope_id TEXT PRIMARY KEY,claim_id TEXT NOT NULL,domain TEXT NOT NULL,purpose TEXT NOT NULL,epistemic_reach_json TEXT NOT NULL,permitted_uses_json TEXT NOT NULL,prohibited_uses_json TEXT NOT NULL,continuation_conditions_json TEXT NOT NULL,correction_routes_json TEXT NOT NULL,release_conditions_json TEXT NOT NULL,reentry_requirements_json TEXT NOT NULL,memory_policy_json TEXT NOT NULL,memory_may_reauthorize INTEGER NOT NULL,operational INTEGER NOT NULL,status TEXT NOT NULL,supersedes_envelope_id TEXT,superseded_by_envelope_id TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,FOREIGN KEY(claim_id) REFERENCES temporal_claims(claim_id));
''');self.c.execute('pragma foreign_keys=on');self.c.commit()
 def _connection(self): return self.c
class Tests(unittest.TestCase):
 def test_plan_deterministic_and_generates_three_envelopes(self):
  a=build_plan(raw());b=build_plan(raw());self.assertEqual(a.draft_sha256,b.draft_sha256);self.assertEqual(a.governance_sha256,b.governance_sha256);self.assertEqual(len(a.envelopes),3);self.assertEqual(a.governance_spec.claim_envelope_ids,[x['envelope_id'] for x in a.envelopes])
 def test_draft_must_bind_exact_account_and_policy_current(self):
  r=raw();r['facts_snapshot']['facts']['signal_email']['account']='other@example.com'
  with self.assertRaises(SignalGovernanceError):build_plan(r)
  r=raw();r['facts_snapshot']['facts']['signal_governance']['policy_current']=False
  with self.assertRaises(SignalGovernanceError):build_plan(r)
 def test_preview_read_only(self):
  db=DB();p=SignalGovernanceBootstrapper(db);before=db.c.total_changes;o=p.preview(raw());self.assertTrue(o['ready_to_seed']);self.assertEqual(before,db.c.total_changes);self.assertFalse(o['authority_change'])
 def test_seed_requires_exact_ceo_digest(self):
  db=DB();p=SignalGovernanceBootstrapper(db);plan=build_plan(raw())
  with self.assertRaises(SignalGovernanceError):p.seed(raw(),expected_draft_sha256=plan.draft_sha256,ceo_confirmed=False)
  with self.assertRaises(SignalGovernanceError):p.seed(raw(),expected_draft_sha256='0'*64,ceo_confirmed=True)
 def test_seed_is_idempotent_and_creates_no_authority_tables(self):
  db=DB();p=SignalGovernanceBootstrapper(db);plan=build_plan(raw());o=p.seed(raw(),expected_draft_sha256=plan.draft_sha256,ceo_confirmed=True);self.assertTrue(o['seeded']);self.assertEqual(db.c.execute('select count(*) from temporal_claims').fetchone()[0],3);self.assertEqual(db.c.execute('select count(*) from temporal_claim_envelopes').fetchone()[0],3);p.seed(raw(),expected_draft_sha256=plan.draft_sha256,ceo_confirmed=True);self.assertEqual(db.c.execute('select count(*) from temporal_claims').fetchone()[0],3)
if __name__=='__main__':unittest.main()
