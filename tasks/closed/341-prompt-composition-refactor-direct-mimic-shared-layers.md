# 341: Prompt composition refactor (direct/mimic/shared layers)

## Summary
Refactor prompt assets and loading so prompt construction is deterministic, layered, and reusable across roles/sessions/protocol prompts.

## Problem
Prompt assets are currently difficult to compose and reuse cleanly. We need a predictable structure that can support multiple framing styles (for example `direct` and `mimic`) while preserving shared technical truth and constraints.

## Goals
- Introduce a clear prompt taxonomy for layered composition.
- Support `direct` and `mimic` framing without duplicating core protocol/schema truth.
- Allow shared constraints/schemas to be composed in a deterministic order.
- Keep common prompt references and CLI behavior predictable during migration.

## Proposed Scope
- Prompt asset layout:
  - `direct/<category>/<name>`
  - `mimic/<category>/<name>`
  - `shared/schemas/<name>`
  - `shared/constraints/<name>`
- Prompt composition engine:
  - deterministic layer order
  - explicit handling of optional vs required layers
- CLI prompt selection surface:
  - `toas prompt <ref> --mode <direct|mimic>`
  - optional compose/introspection path can remain limited in initial pass
- Tests:
  - layer presence/order
  - constraint injection behavior
  - compatibility behavior for legacy refs

## Non-goals (initial pass)
- Full prompt-quality evaluation automation.
- Rich composition explain/debug output beyond minimal correctness needs.

## Migration Notes
- Avoid silent breakage for existing refs in active docs/workflows.
- Prefer explicit compatibility mapping or aliases for moved prompts.
- Make missing required layers fail loudly enough to debug quickly.

## Acceptance Criteria
- Prompt composition works for at least role/session/protocol categories with deterministic ordering.
- `--mode` changes framing as expected while preserving shared technical layers.
- Shared constraint/schema layers can be injected and tested.
- Existing common prompt workflows continue to function (or have documented compatibility mapping).
- Tests cover ordering, optional layers, and failure/compatibility behavior.
