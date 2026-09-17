# Patch 011 — Standing Delegation

Parent candidate: Patch 010 / schema 11.

Schema: **12** via `012_standing_delegation.sql`.

## Purpose

Patch 011 represents reusable, bounded delegation standing for an office such as Signal. It answers whether a role remains **eligible to request a separate execution warrant** for a proposed class of action.

It does **not** mint execution warrants and does not alter the existing external-action gate.

## Core distinction

`Robert delegated this once` is not equivalent to `this action is authorized now`.

A standing delegation remains current only while:

- its own status is active;
- its review boundary has not been reached;
- supporting Claim Envelopes remain current;
- continuation conditions remain satisfied;
- the action type is inside its bounded scope; and
- execution-specific conditions remain satisfied.

Any missing material fact fails closed to review rather than silently inheriting authority.

## Review boundary

`review_by` is not the philosophical basis of authority. It is a mandatory safety boundary for re-evaluating the standing delegation. Reaching it does not auto-renew or erase the historical delegation.

## Non-authority guarantee

A successful standing-delegation assessment produces **eligibility for warrant consideration**, not a warrant. Patch 012 (future) will be responsible for deriving one finite execution warrant, if and only if all required present conditions hold.
