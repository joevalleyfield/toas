# 512: Durable capability grants and layered authorization scopes

Add durable operational grant configuration beyond transcript-only state, with explicit layered scope semantics.

## Why

Transcript-only grant state is insufficient for durable operational policy. We need explicit capability-state records with predictable layering and provenance.

## In scope

- add durable shell/tool grant configuration surface
- define and implement layered scopes:
  - global
  - user
  - workspace
  - head
  - session
  - transient
- represent effective grants as graph-real capability state (not compactable conversation-only projection)
- expose clear diagnostics for effective grants and source attribution per scope layer

## Out of scope

- broad RBAC/user-identity system
- replacing existing grant semantics unrelated to scope layering

## Acceptance Criteria

- durable grant state survives transcript compaction and session churn
- effective grants can be inspected with source/scope attribution
- scope precedence rules are documented and tested
- transcript projection and authoritative operational state are explicitly separated

## Status

Closed (2026-05-15)

## Completed

- Added graph-real shell grant scope records (`shell_scope_grant`) for operational mutations.
- Added scope-aware mutation surface through `/shell ... [--scope ...]` with default `session` scope.
- Added deterministic layered scope resolution order:
  - transient > session > head > workspace > user > global > defaults.
- Switched effective grant resolution away from transcript-line parsing.
- Added result side-effect persistence path for shell scope updates.
- Updated tests to assert operational-state behavior and scoped mutation contracts.
