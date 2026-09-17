# Patch 010 — Claim Envelope / Continuing Evidence Contract

Parent candidate: Patch 009 (schema 10), itself based on Patch 008 commit `a0073017e9d994e649d889d44d681ef5b3b2d0fd`.

Schema: **11** via `011_claim_envelope_continuing_evidence.sql`.

## Purpose

Patch 010 formalizes the minimum contract required before StillPoint introduces standing delegation. It does not create standing delegation and it does not broaden external-action authority.

The governing rule is:

> Every finite exercise of authority must remain answerable to the conditions that authorize its continuation.

## Added distinctions

- **Claim Envelope** — purpose/domain, epistemic reach, bounded permitted uses, structured continuation conditions, correction routes, release conditions, re-entry requirements, and memory policy.
- **Former** — historical or superseded envelopes remain preserved but presently non-governing.
- **Claim-use history** — operational/intervention use must bind the warrant and action that actually used the claim.
- **Description Effect** — later evidence can be marked pre-intervention, post-intervention, mixed, or unknown, with post-intervention evidence linked to prior claim-use events.
- **Memory ≠ reauthorization** — database and Python invariants reject memory as an independent source of operational authority.

## Authority boundary

A current Claim Envelope can establish that a proposed use is in scope and that stated continuation conditions still hold. It **cannot issue, renew, extend, or replace a temporal warrant**. Consequential actions remain governed by StillPoint's existing action/warrant gate.

## Deliberate limits

This patch does not implement standing delegations, automatic warrant minting, schedules, external triggers, or Signal autonomy. Those layers consume this contract later.
