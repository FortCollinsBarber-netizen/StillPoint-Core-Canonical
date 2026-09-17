# Patch 016 — Signal Email Interpretation and Reply Preparation

Patch 016 gives a Signal worker enough vertical behavior to turn one Gmail event into either: no reply, human review, or a reply **proposal**.

It records the interpretation separately from authority. Automated/list/self mail is deterministically suppressed. A provider-backed Signal responder may classify and draft routine correspondence, but its output creates at most an immutable decision record, an `email_body` artifact, and a `send_email` ActionRequest in `waiting_approval`.

Key invariant: **understanding a message and drafting a reply do not authorize sending it.** Standing-delegation evaluation and a separate execution warrant remain later gates.
