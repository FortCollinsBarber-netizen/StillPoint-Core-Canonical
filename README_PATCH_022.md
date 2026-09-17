# Patch 022 — Explicit CEO Signal Governance Pack

Patch 022 adds the authority-provisioning boundary that the production Signal service deliberately refused to invent for itself.

A versioned `stillpoint.signal-governance.v1` policy document names the exact Gmail account, standing delegation ID, trigger ID, supporting Claim Envelopes, continuation conditions, finite autonomous classification set, exclusions, release conditions, review intervals, and initial finite continuation-facts snapshot.

The provisioner supports read-only preview and deterministic SHA-256 calculation. Applying the policy requires both an explicit CEO-confirmation flag and the exact expected digest. A mismatched digest is rejected. Existing IDs are never silently overwritten or broadened; conflicting policy requires a new governance object/revision.

Only the routine classifications `scheduling`, `acknowledgement`, and `routine_information` are eligible to appear in the autonomous allow-set. The provisioner automatically creates machine-enforced execution conditions binding the exact Gmail account, a prepared reply, `requires_human=false`, and the finite classification set.

The supporting Claim Envelopes must already exist and remain active inside the authority-changing transaction. The service trigger is bounded inside the delegation review interval. The finite facts snapshot cannot outlive the delegation review interval.

Commands:
- `python -m stillpoint.signal_governance preview SPEC.json`
- `python -m stillpoint.signal_governance apply SPEC.json --facts-file /absolute/path --confirm-sha <digest> --confirm-ceo`
