import json,sqlite3,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
NOW=datetime.now(timezone.utc);PAST=(NOW-timedelta(hours=1)).isoformat();FUT=(NOW+timedelta(hours=1)).isoformat()
class Tests(unittest.TestCase):
 def setUp(self):
  c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row;self.c=c
  c.executescript('''
 CREATE TABLE temporal_claim_envelopes(envelope_id TEXT PRIMARY KEY,status TEXT);
 CREATE TABLE standing_delegations(delegation_id TEXT PRIMARY KEY,status TEXT,valid_from TEXT,review_by TEXT);
 CREATE TABLE standing_delegation_evaluations(evaluation_id TEXT PRIMARY KEY,delegation_id TEXT,evaluated_at TEXT,action_id TEXT,action_type TEXT,action_target TEXT,facts_sha256 TEXT,result TEXT,action_in_scope INTEGER,supporting_envelopes_json TEXT);
 CREATE TABLE temporal_warrants(warrant_id TEXT PRIMARY KEY,status TEXT,valid_from TEXT,valid_to TEXT,scope_json TEXT);
 CREATE TABLE action_requests(id TEXT PRIMARY KEY,action_type TEXT,target TEXT,status TEXT,authorization_mode TEXT,standing_delegation_id TEXT,standing_evaluation_id TEXT,warrant_id TEXT);
 ''')
  digest='a'*64;c.execute("insert into temporal_claim_envelopes values('env','active')");c.execute("insert into standing_delegations values('del','active',?,?)",(PAST,FUT));c.execute("insert into standing_delegation_evaluations values('eval','del',?,'act','send_email','target',?,'current',1,'[\"env\"]')",(NOW.isoformat(),digest));c.execute("insert into temporal_warrants values('w','active',?,?,?)",(PAST,FUT,json.dumps({'standing_delegation_id':'del','standing_evaluation_id':'eval','standing_facts_sha256':digest})));c.execute("insert into action_requests values('act','send_email','target','ready_for_action','standing_delegation','del','eval','w')");c.executescript((Path(__file__).parents[1]/'migrations'/'018_delegated_dispatch_revalidation.sql').read_text());c.commit()
 def tearDown(self):self.c.close()
 def dispatch(self):self.c.execute("update action_requests set status='dispatching' where id='act'");self.c.commit()
 def test_current_lineage_can_cross_dispatch_boundary(self):self.dispatch();self.assertEqual(self.c.execute("select status from action_requests").fetchone()[0],'dispatching')
 def test_revoked_delegation_blocks_dispatch(self):
  self.c.execute("update standing_delegations set status='revoked'");self.c.commit()
  with self.assertRaises(sqlite3.DatabaseError):self.dispatch()
  self.c.rollback()
 def test_former_envelope_blocks_dispatch(self):
  self.c.execute("update temporal_claim_envelopes set status='historical'");self.c.commit()
  with self.assertRaises(sqlite3.DatabaseError):self.dispatch()
  self.c.rollback()
 def test_newer_failed_evaluation_blocks_dispatch(self):
  later=(NOW+timedelta(seconds=1)).isoformat();self.c.execute("insert into standing_delegation_evaluations values('eval2','del',?,'act','send_email','target',?,'review_required',0,'[\"env\"]')",(later,'b'*64));self.c.commit()
  with self.assertRaises(sqlite3.DatabaseError):self.dispatch()
  self.c.rollback()
 def test_inactive_warrant_blocks_dispatch(self):
  self.c.execute("update temporal_warrants set status='revoked'");self.c.commit()
  with self.assertRaises(sqlite3.DatabaseError):self.dispatch()
  self.c.rollback()
 def test_facts_digest_mismatch_blocks_dispatch(self):
  self.c.execute("update temporal_warrants set scope_json=?",(json.dumps({'standing_delegation_id':'del','standing_evaluation_id':'eval','standing_facts_sha256':'b'*64}),));self.c.commit()
  with self.assertRaises(sqlite3.DatabaseError):self.dispatch()
  self.c.rollback()
if __name__=='__main__':unittest.main()
