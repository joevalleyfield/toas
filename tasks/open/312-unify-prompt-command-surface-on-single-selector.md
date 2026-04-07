## Goal

Unify prompt navigation/rendering on `/prompt` as the single selector command, with branch-on-leaf behavior, while preserving `/prompts` as compatibility alias.

## Why Now

`/model` is moving to single-selector semantics. Prompt browsing should match the same interaction model to reduce command-surface cognitive load.

## Scope

- make `/prompt` the primary command:
  - `/prompt` -> list top-level prompt namespaces/options
  - `/prompt <prefix>` -> list children when non-leaf
  - `/prompt <leaf_ref>` -> render prompt content when leaf
- keep `/prompts [prefix]` as compatibility alias initially
- update help/docs to prefer `/prompt`
- ensure generated next-step guidance emits `/prompt ...` lines by default

## Intended Inputs

- prompt browse/render command handling in `src/toas/step.py`
- prompt asset helpers in `src/toas/prompts.py`
- tests in `tests/test_step.py` / prompt-related suites

## Intended Outputs

- consistent single-selector command pattern
- reduced surface-area confusion between browse vs select verbs
- backward-compatible transition path for existing `/prompts` usage

## Constraints

- no prompt content or library-format changes in this task
- maintain existing behavior for leaf rendering correctness
- alias period should be explicit and documented

## Non-Goals

- no immediate removal of `/prompts`
- no UI-level picker; command-line flow only

## Done When

- `/prompt` supports both navigation and leaf render paths
- `/prompts` continues to work as alias during transition
- help/docs and tests reflect `/prompt` as canonical surface
