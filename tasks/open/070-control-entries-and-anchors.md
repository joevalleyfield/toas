## Goal

Represent non-message operator state inside durable history instead of sidecar files.

## Scope

- Define durable record shapes for binding overrides and anchors
- Move `jump` state out of `jump.txt` and into append-only history
- Add anchor records for transcript offset to message binding
- Teach log readers to distinguish message events from non-message records

## Shape

Control record:
- kind: `jump` | `anchor`
- payload: dict
- related_to: optional[str]

## Rules

- Control records are append-only
- Control records do not become transcript blocks
- `jump` is explicit semantic override, not inferred sameness
- Anchors accelerate alignment/projection but do not change message causality

## Non-Goals

- No heavy indexing system yet
- No branch visualization yet

## Done When

- `toas jump N` no longer depends on a sidecar file
- The active binding override can be derived from history
- Anchor records can be appended and ignored safely by transcript-facing code
