## Goal

Deepen model capability-space configuration from a shallow single/default model source into a structured catalog that powers `/model` discovery and selection while preserving deferred frontier validation.

## Why Now

Current model population is intentionally minimal (configured default + env list). As usage expands, TOAS needs richer model metadata and explicit capability-space management without regressing current behavior.

## Scope

- add structured model catalog support in config (for example `llm.models`)
- keep existing `llm.model` baseline/default behavior for backward compatibility
- update `/model` selection/listing logic to prefer catalog entries
- preserve deferred validation at inference frontier
- improve unavailable-model continuation UX using catalog-derived alternatives

## Intended Behavior

- config can define multiple models with metadata (initially minimal, extensible later):
  - `id` (required)
  - optional `label`, `tags`, `notes`, capability hints
- `/model` with no args lists configured capability space in stable order
- `/model <id>` records transcript intent as today
- frontier validates only when model is consumed by inference
- if unavailable at frontier, TOAS presents explicit continuation choices from current capability space

## Intended Inputs

- `src/toas/config.py`
- `src/toas/step.py`
- `src/toas/cli.py`
- prompt/help surfaces and docs (`README.md` etc.)
- tests for config parsing and `/model` behavior

## Intended Outputs

- richer model discovery/selection experience
- stronger alignment between `/config` capability definition and `/model` transcript state
- backward compatibility with existing shallow model configuration

## Constraints

- preserve current config compatibility
- maintain append-only transcript/history semantics
- avoid eager capability validation outside inference frontier

## Non-Goals

- no provider-side dynamic model discovery requirement in first pass
- no automatic migration tool requirement in first pass

## Done When

- structured model catalog parsed from config and covered by tests
- `/model` list/selection works against catalog with fallback compatibility
- frontier unavailable-model continuation uses catalog alternatives
- docs reflect define-vs-select model semantics clearly
