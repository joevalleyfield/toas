# 514: Operational state vs conversational projection boundary

Define and enforce the boundary between compactable conversational projection and authoritative operational state.

## Why

Operational control (grants/config/session-control facts) must remain authoritative even when conversation projection is compacted or rewritten.

## In scope

- document the state taxonomy: conversational vs operational
- audit current records and identify boundary leaks
- define migration path for any operationally authoritative state currently encoded only in transcript projection
- add tests that protect boundary invariants

## Out of scope

- unrelated compaction algorithm redesign
- broad graph schema rewrite beyond required boundary hardening

## Acceptance Criteria

- boundary policy is documented and linked from roadmap/architecture notes
- operationally authoritative state is graph-real and queryable
- compaction/projection flows preserve operational correctness
- regression tests protect identified boundary invariants

## Status

Closed (2026-05-15)

## Completed

- Codified boundary behavior: shell grants are now operationally authoritative and not transcript-derived.
- Added an architecture note documenting conversational vs operational state and scope precedence:
  - `docs/notes/2026-05-15-operational-state-vs-conversational-projection.md`
- Updated runtime behavior/tests so transcript compaction/projection no longer acts as shell grant authority.
