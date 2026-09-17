from __future__ import annotations

import json
import sqlite3
import unittest
from pathlib import Path

from stillpoint.authority.delegated_warrants import (
    DelegatedAuthorizationError,
    DelegatedWarrantIssuer,
    validate_delegated_warrant_current,
)

T0="2026-09-17T16:00:00+00:00"
T30="2026-09-17T16:00:30+00:00"
T2="2026-10-01T16:00:00+00:00"

class DB:
    def __init__(self,c):self.c=c
    def _connection(self):return self.c

class Patch012Tests(unittest.TestCase):
    def setUp(self):
        c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');self.c=c
        c.executescript('''
        CREATE TABLE temporal_claims (
          claim_id TEXT PRIMARY KEY,evidence_refs_json TEXT NOT NULL DEFAULT '[]'
        );
        CREATE TABLE temporal_warrants (
          warrant_id TEXT PRIMARY KEY,domain TEXT NOT NULL,action_class TEXT NOT NULL,subject TEXT NOT NULL,
          target TEXT,claim_ids_json TEXT NOT NULL DEFAULT '[]',evidence_ids_json TEXT NOT NULL DEFAULT '[]',
          issuer TEXT,policy_basis TEXT,issued_at TEXT NOT NULL,valid_from TEXT NOT NULL,valid_to TEXT,status TEXT NOT NULL,
          scope_json TEXT NOT NULL DEFAULT '{}',completion_condition TEXT,provenance_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL,updated_at TEXT NOT NULL,superseded_by TEXT,revoked_reason TEXT,completed_at TEXT
        );
        CREATE TABLE action_requests (
          id TEXT PRIMARY KEY,task_id TEXT NOT NULL,action_type TEXT NOT NULL,target TEXT NOT NULL,
          scope_json TEXT NOT NULL,artifact_refs_json TEXT NOT NULL,approval_required INTEGER NOT NULL,
          approval_id TEXT,expires_at TEXT NOT NULL,issued_at TEXT NOT NULL,authority_revision TEXT NOT NULL,
          status TEXT NOT NULL,warrant_id TEXT,warrant_bound_at TEXT,updated_at TEXT NOT NULL
        );
        CREATE TABLE temporal_evidence(evidence_id TEXT PRIMARY KEY);
        INSERT INTO temporal_claims VALUES('claim-1','[{"evidence_id":"ev-1"}]');
        INSERT INTO temporal_evidence VALUES('ev-1');
        INSERT INTO action_requests VALUES(
          'action-1','task-1','send_email','person@example.com','["recipient=person@example.com"]','[]',1,NULL,
          '2026-09-17T17:00:00+00:00','2026-09-17T15:59:00+00:00','rev-1','waiting_approval',NULL,NULL,'2026-09-17T16:00:00+00:00'
        );
        ''')
        # Claim envelope schema subset required by issuer/validator.
        c.executescript('''
        CREATE TABLE temporal_claim_envelopes(
          envelope_id TEXT PRIMARY KEY,claim_id TEXT NOT NULL,status TEXT NOT NULL
        );
        INSERT INTO temporal_claim_envelopes VALUES('env-1','claim-1','active');
        CREATE TABLE standing_delegations(
          delegation_id TEXT PRIMARY KEY,delegate_role TEXT,issuer TEXT,policy_basis TEXT,purpose TEXT,
          claim_envelope_ids_json TEXT,allowed_action_types_json TEXT,continuation_conditions_json TEXT,
          execution_conditions_json TEXT,exclusions_json TEXT,release_conditions_json TEXT,
          valid_from TEXT NOT NULL,review_by TEXT NOT NULL,status TEXT NOT NULL
        );
        INSERT INTO standing_delegations VALUES(
          'del-1','signal','CEO:Robert Emmanuel LaDay','CEO standing delegation','ordinary email',
          '["env-1"]','["send_email"]','[{}]','[{}]','[]','["revocation"]',
          '2026-09-17T15:00:00+00:00','2026-10-01T16:00:00+00:00','active'
        );
        CREATE TABLE standing_delegation_evaluations(
          evaluation_id TEXT PRIMARY KEY,delegation_id TEXT NOT NULL,evaluated_at TEXT NOT NULL,
          action_id TEXT NOT NULL,action_type TEXT NOT NULL,action_target TEXT NOT NULL,facts_sha256 TEXT NOT NULL,
          result TEXT NOT NULL,action_in_scope INTEGER NOT NULL,failed_conditions_json TEXT NOT NULL,
          supporting_envelopes_json TEXT NOT NULL,note TEXT
        );
        INSERT INTO standing_delegation_evaluations VALUES(
          'eval-1','del-1','2026-09-17T16:00:00+00:00','action-1','send_email','person@example.com',
          'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','current',1,'[]','["env-1"]','ok'
        );
        ''')
        migration=Path(__file__).resolve().parents[1]/'migrations'/'013_delegated_execution_warrant.sql'
        c.executescript(migration.read_text())
        self.db=DB(c);self.issuer=DelegatedWarrantIssuer(self.db)

    def tearDown(self):self.c.close()

    def issue(self,**kw):
        args=dict(action_id='action-1',delegation_id='del-1',evaluation_id='eval-1',now_iso=T30,ttl_seconds=300,max_evaluation_age_seconds=60);args.update(kw)
        return self.issuer.authorize_waiting_action(**args)

    def test_issues_one_short_lived_warrant_without_ceo_approval(self):
        w=self.issue()
        row=dict(self.c.execute("select * from action_requests where id='action-1'").fetchone())
        self.assertEqual(row['authorization_mode'],'standing_delegation')
        self.assertEqual(row['approval_required'],0);self.assertIsNone(row['approval_id'])
        self.assertEqual(row['warrant_id'],w.warrant_id);self.assertEqual(row['status'],'ready_for_action')
        self.assertEqual(w.scope['max_actions'],1)
        self.assertEqual(w.scope['standing_delegation_id'],'del-1')
        self.assertEqual(w.claim_ids,['claim-1']);self.assertEqual(w.evidence_ids,['ev-1'])
        self.assertEqual(self.c.execute('select count(*) from delegated_warrant_issuances').fetchone()[0],1)

    def test_stale_evaluation_is_rejected(self):
        with self.assertRaises(DelegatedAuthorizationError):
            self.issue(now_iso='2026-09-17T16:02:00+00:00')

    def test_newer_failed_evaluation_supersedes_old_current_evaluation(self):
        self.c.execute("insert into standing_delegation_evaluations values(?,?,?,?,?,?,?,?,?,?,?,?)",(
          'eval-2','del-1','2026-09-17T16:00:20+00:00','action-1','send_email','person@example.com',
          'b'*64,'review_required',0,'["condition_failed"]','["env-1"]','changed'))
        self.c.commit()
        with self.assertRaises(DelegatedAuthorizationError):self.issue()

    def test_evaluation_cannot_be_reused_for_different_action(self):
        self.c.execute("insert into action_requests(id,task_id,action_type,target,scope_json,artifact_refs_json,approval_required,approval_id,expires_at,issued_at,authority_revision,status,warrant_id,warrant_bound_at,updated_at) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(
          'action-2','task-1','send_email','other@example.com','[]','[]',1,None,'2026-09-17T17:00:00+00:00',T0,'rev-1','waiting_approval',None,None,T0))
        self.c.commit()
        with self.assertRaises(DelegatedAuthorizationError):
            self.issuer.authorize_waiting_action(action_id='action-2',delegation_id='del-1',evaluation_id='eval-1',now_iso=T30)

    def test_revocation_after_issuance_blocks_dispatch_revalidation(self):
        w=self.issue()
        action=dict(self.c.execute("select * from action_requests where id='action-1'").fetchone())
        self.c.execute("update standing_delegations set status='revoked' where delegation_id='del-1'");self.c.commit()
        with self.assertRaises(DelegatedAuthorizationError):
            validate_delegated_warrant_current(db=self.db,action_row=action,warrant=w,now_iso=T30)

    def test_former_supporting_envelope_blocks_issuance(self):
        self.c.execute("update temporal_claim_envelopes set status='historical' where envelope_id='env-1'");self.c.commit()
        with self.assertRaises(DelegatedAuthorizationError):self.issue()

    def test_issuance_history_is_append_only(self):
        self.issue()
        with self.assertRaises(sqlite3.DatabaseError):
            self.c.execute("delete from delegated_warrant_issuances")
        self.c.rollback()

if __name__=='__main__':unittest.main()
