## Goal

Add a first-class non-message intent lane for session-level goals (task/arc/mission metadata) that remains durable and queryable without overloading message events.

## Status Note

Complete (2026-05-09). Core lane durability, operator `/intent` command surface, CLI mirror (`toas intents`), projection/observability integration, and docs stitching are all landed.

## Why

`456` completed transcript path decoupling; next operator need is durable expressed intent independent of message content.

## Scope

- define durable intent record shape and append semantics
- keep intent records distinct from message-event numbering/lineage
- add lightweight query/projection surfaces for recent/active intents
- test append, query, and projection invariants

## Non-Goals (This Task)

- no hard coupling to repo task files, GitHub issues, Jira, or other trackers
- no automatic bidirectional sync with external intent systems
- no ranking/scoring policy for intent selection beyond explicit status and recency
- no replay/queue arbitration redesign (covered by existing `442` / `443` work)

## Proposed Record Shape (Initial)

Durable `intent` lane record (append-only, non-message):

- `type`: `intent`
- `id`: stable record id (event id)
- `parent`: lineage parent in durable history
- `timestamp`: append timestamp
- `intent` object:
  - `intent_id`: operator-facing handle (`iN` projection alias allowed)
  - `title`: short goal text
  - `status`: `active|paused|completed|cancelled`
  - `scope` (optional): short scope hint (`task|arc|mission|session`)
  - `tags` (optional): string list
  - `source` (optional): opaque source hint (`task:462`, `manual`, etc.)
  - `notes` (optional): short operator note

Notes:
- keep canonical storage minimal and forward-compatible
- avoid embedding message-event numbering in intent payloads
- projection may add friendly aliases (`#i1`) without changing durable shape

## Operator Surfaces (Initial)

CLI/session surfaces should be intentionally lightweight:

- append/update:
  - `/intent set <title> [--status ...] [--scope ...] [--tag ...] [--source ...]`
  - `/intent status <intent_id|current> <active|paused|completed|cancelled>`
  - `/intent note <intent_id|current> <text>`
- inspect:
  - `/intent list [--all|--active|--recent N]`
  - `/intent current`
  - optional CLI mirror: `toas intents` with similar filters

Design bias:
- append new intent records for state transitions; never mutate prior records
- "current intent" is derived deterministically (latest `active` not superseded)

## Invariants

- intent records do not participate in message numbering
- intent records do not alter message parentage/lineage semantics
- transcript/message projection remains behaviorally stable when no intent commands are present
- intent query order is deterministic by durable append order and status transitions

## Implementation Slices

1. Storage + query seam
- add durable `intent` record constructor/append helper
- add query helper(s): recent intents, active intent resolution, by-id lookup
- add unit tests for append/query determinism

2. Operator command surface
- add `/intent` command family (set/status/note/list/current) via runtime operator command handlers
- return compact operator-facing projections
- add parser and handler tests for success/error paths

3. Optional CLI mirror
- add `toas intents` read surface for non-transcript inspection
- align output style with existing compact list/report commands
- add CLI contract tests

4. Projection + observability integration
- ensure history/outline/session projections can expose intent handle when useful (non-invasive)
- keep behavior additive and low-noise
- add targeted projection tests

5. Documentation + roadmap stitching
- update task progress and done checklist
- update `docs/capabilities.md` for new intent surface once landed
- update roadmap active focus note when task reaches substantive milestone

## Test Matrix

- storage append:
  - appending first intent
  - appending multiple updates to same logical intent
  - mixed record streams (message/tool/control/intent)
- query behavior:
  - active intent derivation across status transitions
  - recent ordering and filter correctness
  - by-id not found diagnostics
- operator command behavior:
  - `/intent set` required/optional args
  - `/intent status` state transitions
  - `/intent note` note append path
  - `/intent list` filter options
  - `/intent current` empty vs present behavior
- invariants:
  - message lineage numbering unchanged after intent appends
  - no regressions in existing step/rebuild projections

## Done When

- intent records can be appended durably
- operators can inspect active/recent intents via CLI/session surface
- tests prove no message-lineage semantic drift

## Progress Checklist

- [x] slice 1: storage + query seam
- [x] slice 2: operator `/intent` command family
- [x] slice 3: optional `toas intents` mirror
- [x] slice 4: projection/observability integration
- [x] slice 5: docs + roadmap stitching
