## Goal

Turn the current coherent core into an intentional operator runtime with explicit lineage control and practical projection behavior.

## Scope

- Surface lineage and head selection more explicitly
- Put anchors to real use in projection and alignment
- Tighten branch-aware continuation from non-tip heads
- Clarify which projections belong on the operator surface

## Why

The core storage model is now in place, but the runtime still behaves more like a promising prototype than a deliberate operator. Milestone 1 should make branch-aware use of history practical before the broader LLM/tool/prompt tracks expand the system.

## Planned Tasks

- `111`: explicit head selection and inspection
- `112`: anchor-backed alignment and projection shortcuts
- `113`: non-tip continuation semantics at the operator boundary
- `114`: transcript/history projection commands

## Non-Goals

- No merge semantics
- No heavy branch UI
- No multi-provider model integration yet

## Done When

- A user can explicitly inspect and select the lineage head they are working from
- Anchors are used for real runtime shortcuts rather than only stored as inert records
- Continuation from non-tip lineages is explicit and predictable
- Projection behavior is available as a practical operator surface, not only internal helpers
