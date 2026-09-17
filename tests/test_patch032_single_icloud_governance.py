import json,sqlite3,tempfile,unittest
from pathlib import Path
from stillpoint.signal_mail_governance_policy import (
    DRAFT_SCHEMA, POLICY_SCHEMA, CEO_ISSUER, build_bootstrap_plan,
    SignalMailGovernanceProvisioner, SignalMailGovernanceError,
)

DRAFT_PATH=Path(__file__).resolve().parent/'fixtures'/'signal_icloud_personal_business.draft.json'
def raw(): return json.loads(DRAFT_PATH.read_text())

class DB:
    def __init__(self):
        self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row;self.c.execute('pragma foreign_keys=on')
        self.c.executescript('''
CREATE TABLE temporal_claims(claim_id TEXT PRIMARY KEY,subject TEXT NOT NULL,predicate TEXT NOT NULL,value_json TEXT,domain TEXT NOT NULL,source TEXT NOT NULL,evidence_refs_json TEXT NOT NULL DEFAULT '[]',time_observed TEXT,time_asserted TEXT NOT NULL,effective_from TEXT,effective_to TEXT,confidence REAL,status TEXT NOT NULL,supersedes TEXT,superseded_by TEXT,review_conditions_json TEXT NOT NULL DEFAULT '[]',provenance_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE temporal_claim_envelopes(envelope_id TEXT PRIMARY KEY,claim_id TEXT NOT NULL,domain TEXT NOT NULL,purpose TEXT NOT NULL,epistemic_reach_json TEXT NOT NULL,permitted_uses_json TEXT NOT NULL,prohibited_uses_json TEXT NOT NULL,continuation_conditions_json TEXT NOT NULL,correction_routes_json TEXT NOT NULL,release_conditions_json TEXT NOT NULL,reentry_requirements_json TEXT NOT NULL,memory_policy_json TEXT NOT NULL,memory_may_reauthorize INTEGER NOT NULL,operational INTEGER NOT NULL,status TEXT NOT NULL,supersedes_envelope_id TEXT,superseded_by_envelope_id TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,FOREIGN KEY(claim_id) REFERENCES temporal_claims(claim_id));
CREATE TABLE standing_delegations(delegation_id TEXT PRIMARY KEY,delegate_role TEXT,issuer TEXT,policy_basis TEXT,purpose TEXT,claim_envelope_ids_json TEXT,allowed_action_types_json TEXT,continuation_conditions_json TEXT,execution_conditions_json TEXT,exclusions_json TEXT,release_conditions_json TEXT,valid_from TEXT,review_by TEXT,status TEXT,supersedes_delegation_id TEXT,created_at TEXT,updated_at TEXT);
CREATE TABLE trigger_definitions(trigger_id TEXT PRIMARY KEY,owner_role TEXT,trigger_kind TEXT,source TEXT,event_type TEXT,goal_template TEXT,project TEXT,status TEXT,valid_from TEXT,review_by TEXT,next_run_at TEXT,interval_seconds INTEGER,max_runs INTEGER,run_count INTEGER,catch_up_policy TEXT,metadata_json TEXT,created_at TEXT,updated_at TEXT);
''');self.c.commit()
    def _connection(self): return self.c

class Tests(unittest.TestCase):
    def test_exact_ceo_topology_is_one_icloud_mailbox(self):
        plan=build_bootstrap_plan(raw());s=plan.governance_spec
        self.assertEqual(s.identity.provider,'icloud');self.assertEqual(s.identity.account,'fortcollinsbarber@icloud.com');self.assertEqual(s.identity.jurisdiction,'personal_business')
        self.assertEqual(set(s.allowed_classifications),{'scheduling','acknowledgement','routine_information'})
    def test_ccu_gmail_is_not_in_policy(self):
        payload=json.dumps(raw()).lower();self.assertNotIn('students.ccu.edu',payload);self.assertNotIn('gmail',payload)
    def test_bootstrap_is_deterministic_and_non_authorizing(self):
        a=build_bootstrap_plan(raw());b=build_bootstrap_plan(raw());self.assertEqual(a.draft_sha256,b.draft_sha256);self.assertEqual(a.governance_sha256,b.governance_sha256);self.assertEqual(len(a.envelopes),3)
        db=DB();p=SignalMailGovernanceProvisioner(db);before=db.c.total_changes;o=p.preview_seed(raw());self.assertFalse(o['authority_change']);self.assertEqual(before,db.c.total_changes)
    def test_facts_must_bind_exact_provider_account_and_jurisdiction(self):
        for key,value in [('provider','gmail'),('account','other@icloud.com'),('jurisdiction','business')]:
            r=raw();r['facts_snapshot']['facts']['signal_mail'][key]=value
            with self.assertRaises(SignalMailGovernanceError):build_bootstrap_plan(r)
    def test_seed_creates_claims_only_then_apply_requires_exact_ceo_digest(self):
        db=DB();p=SignalMailGovernanceProvisioner(db);plan=build_bootstrap_plan(raw())
        with self.assertRaises(SignalMailGovernanceError):p.seed(raw(),expected_draft_sha256=plan.draft_sha256,ceo_confirmed=False)
        seeded=p.seed(raw(),expected_draft_sha256=plan.draft_sha256,ceo_confirmed=True);self.assertTrue(seeded['seeded']);self.assertEqual(db.c.execute('select count(*) from standing_delegations').fetchone()[0],0)
        spec=plan.governance_spec
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'facts.json'
            with self.assertRaises(SignalMailGovernanceError):p.apply(spec,facts_file=f,expected_sha256='0'*64,ceo_confirmed=True)
            out=p.apply(spec,facts_file=f,expected_sha256=spec.digest(),ceo_confirmed=True);self.assertTrue(out['applied'])
            self.assertEqual(db.c.execute('select count(*) from standing_delegations').fetchone()[0],1);self.assertEqual(db.c.execute('select count(*) from trigger_definitions').fetchone()[0],1)
            t=db.c.execute('select source,event_type from trigger_definitions').fetchone();self.assertEqual((t['source'],t['event_type']),('icloud','message_received'))
    def test_machine_conditions_bind_single_mailbox(self):
        s=build_bootstrap_plan(raw()).governance_spec;c={x.key:(x.operator.value,x.expected) for x in s.execution_conditions()}
        self.assertEqual(c['signal_email.provider'],('eq','icloud'));self.assertEqual(c['signal_email.account'],('eq','fortcollinsbarber@icloud.com'));self.assertEqual(c['signal_email.jurisdiction'],('eq','personal_business'));self.assertEqual(c['signal_email.requires_human'],('eq',False))

if __name__=='__main__':unittest.main()
