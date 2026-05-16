# Doc Truth Model (Fact vs Direction vs Draft)

Status: CURRENT
Task Link: `516`

## Purpose

Prevent ambiguity during rearchitecture by making document intent explicit and enforceable.

## Status Classes

- `CURRENT`
  - normative current behavior
  - should match implemented code paths
  - should not contain speculative future behavior without explicit callouts

- `DIRECTIONAL`
  - target-state architecture and sequencing intent
  - non-normative for current behavior
  - must link to open task(s) that operationalize the direction

- `DRAFT`
  - proposed contract/design under active shaping
  - may change before implementation
  - must link to open task(s) and identify unresolved questions

## Coupling Rules

- Planned sections in `DIRECTIONAL`/`DRAFT` docs must reference at least one open task ID.
- When implementation lands, update status/sections and add closure linkage (task + commit).
- Current behavior belongs in `docs/capabilities.md`; roadmap/direction docs should not be treated as capability truth.

