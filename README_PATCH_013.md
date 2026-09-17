# Patch 013 — Schedules and Event Triggers

Parent candidate: Patch 012 / schema 13.
Schema: **14** via `014_schedules_and_event_triggers.sql`.

Patch 013 lets StillPoint generate internal work without Robert opening a chat first. It adds durable event ingestion, interval schedules, idempotent trigger firing, and trigger-to-task context.

## Authority boundary

A trigger can create an ordinary `tasks` row. It cannot create an ActionRequest, standing delegation, approval, or temporal warrant. An inbound email therefore has standing to *wake Signal up*, not to authorize Signal to reply.

## Event path

`external event -> immutable inbound_event -> matching trigger -> ordinary task -> worker lease -> normal StillPoint planning/authority path`

Duplicate provider events collapse through a stable `dedupe_key`. A trigger/event pair fires at most once.

## Schedule path

The first schedule implementation is bounded interval scheduling with a minimum 60-second interval and `coalesce` catch-up behavior. After downtime, a due schedule creates one task and advances to the next future slot instead of manufacturing an unbounded backlog.

Each trigger has `valid_from` and `review_by`; reaching the review boundary stops new firing rather than silently renewing the trigger forever.
