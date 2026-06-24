Filed as: 463-session-identity-orchestration-and-buffer-mapping
FKA: 463-session-identity-orchestration-and-buffer-mapping
AKA: session identity; multi-buffer; session mapping
Legacy index: 463

keywords: surface, exploration, parked, research, identity, session

# Session Identity Orchestration and Buffer Mapping

Define and implement named/multi-buffer session identity semantics (for example `.toas/session-<name>.md`) while preserving canonical `events.jsonl` authority.

## Why

`456` established configurable transcript paths; next step is ergonomic multi-buffer identity and selection.

## Scope

- define session-identity mapping model (slot/name/path)
- implement selection and persistence semantics
- clarify lineage/head/anchor interactions under identity switches
- add tests for deterministic selection and compatibility defaults

## Done When

- operators can switch among named/slot session identities deterministically
- identity changes are observable and test-covered
- compatibility with existing single-transcript workflows is preserved
