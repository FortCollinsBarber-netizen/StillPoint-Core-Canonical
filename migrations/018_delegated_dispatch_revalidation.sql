-- 018_delegated_dispatch_revalidation.sql
-- Revalidate standing-delegation lineage inside the durable dispatch transition.
-- Closes the revocation/evidence TOCTOU gap between Python preflight and dispatch commit.

CREATE TRIGGER IF NOT EXISTS trg_standing_dispatch_requires_current_lineage
BEFORE UPDATE OF status ON action_requests
WHEN NEW.status='dispatching' AND NEW.authorization_mode='standing_delegation'
BEGIN
    SELECT CASE WHEN NEW.standing_delegation_id IS NULL OR NEW.standing_evaluation_id IS NULL OR NEW.warrant_id IS NULL
      THEN RAISE(ABORT,'delegated dispatch missing lineage') END;
    SELECT CASE WHEN NOT EXISTS (
      SELECT 1 FROM standing_delegations d
      WHERE d.delegation_id=NEW.standing_delegation_id
        AND d.status='active'
        AND julianday(d.valid_from) <= julianday('now')
        AND julianday(d.review_by) > julianday('now')
    ) THEN RAISE(ABORT,'standing delegation no longer current at dispatch') END;
    SELECT CASE WHEN NOT EXISTS (
      SELECT 1 FROM standing_delegation_evaluations e
      WHERE e.evaluation_id=NEW.standing_evaluation_id
        AND e.delegation_id=NEW.standing_delegation_id
        AND e.action_id=NEW.id
        AND e.action_type=NEW.action_type
        AND e.action_target=NEW.target
        AND e.result='current' AND e.action_in_scope=1
    ) THEN RAISE(ABORT,'standing evaluation no longer supports dispatch') END;
    SELECT CASE WHEN EXISTS (
      SELECT 1 FROM standing_delegation_evaluations newer
      JOIN standing_delegation_evaluations bound ON bound.evaluation_id=NEW.standing_evaluation_id
      WHERE newer.delegation_id=NEW.standing_delegation_id AND newer.action_id=NEW.id
        AND (newer.evaluated_at > bound.evaluated_at OR (newer.evaluated_at=bound.evaluated_at AND newer.evaluation_id>bound.evaluation_id))
    ) THEN RAISE(ABORT,'newer standing evaluation exists at dispatch') END;
    SELECT CASE WHEN EXISTS (
      SELECT 1
      FROM standing_delegation_evaluations e, json_each(e.supporting_envelopes_json) j
      LEFT JOIN temporal_claim_envelopes env ON env.envelope_id=j.value
      WHERE e.evaluation_id=NEW.standing_evaluation_id
        AND (env.envelope_id IS NULL OR env.status!='active')
    ) THEN RAISE(ABORT,'supporting claim envelope no longer current at dispatch') END;
    SELECT CASE WHEN NOT EXISTS (
      SELECT 1 FROM temporal_warrants w JOIN standing_delegation_evaluations e ON e.evaluation_id=NEW.standing_evaluation_id
      WHERE w.warrant_id=NEW.warrant_id AND w.status='active'
        AND julianday(w.valid_from) <= julianday('now') AND julianday(w.valid_to) > julianday('now')
        AND json_extract(w.scope_json,'$.standing_delegation_id')=NEW.standing_delegation_id
        AND json_extract(w.scope_json,'$.standing_evaluation_id')=NEW.standing_evaluation_id
        AND json_extract(w.scope_json,'$.standing_facts_sha256')=e.facts_sha256
    ) THEN RAISE(ABORT,'delegated warrant no longer current or lineage digest mismatch') END;
END;
