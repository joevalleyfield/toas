## Goal

Clean up operation schema naming and intent placement so structured calls are concise and unambiguous.

## Why Now

`arguments` is ambiguous (tool args vs shell args), and intent should be first-class across all operations.

## Scope

- establish operation-level `intent` as first-class optional metadata for any operation
- evaluate and land naming cleanup from `arguments` to `params` for tool payloads
- support compact shell `command` sugar without creating a separate authorization model
- define validation rules for shell payload variants (`argv` vs string form) to avoid ambiguous mixes

## Intended Behavior

- every operation type can include `intent`
- tool payload naming is clearer and less collision-prone
- shell compact and structured forms normalize to the same internal execution model

## Constraints

- preserve backward compatibility where feasible (compat aliases/deprecation path)
- avoid schema churn that breaks existing transcripts without migration strategy

## Done When

- schema docs reflect `intent` and cleaned payload naming
- parser/normalizer supports compatibility path with clear diagnostics
- tests cover new canonical shape and backward-compatible legacy forms

## Progress

- 2026-04-24: First slice landed.
- Parser normalization now accepts `params` alongside `args`/`arguments` and accepts `intent` alongside `intention` (with explicit conflict diagnostics).
- Shell-call normalization now rejects ambiguous `argv` + `command`/`cmd` mixes and normalizes `args.command`/`args.cmd` to canonical `argv` for `shell`.
- Capability/usage copy now advertises `params` and `intent` aliases.
- Regression coverage added for new aliases and ambiguity checks (`tests/test_graph.py`, `tests/test_tools_execution.py`, `tests/test_tools_rendering.py`, prompt capability-copy assertion updates).
- 2026-04-24: Documentation completion slice landed.
- README now documents canonical callable shape (`operation` + `params` + optional `intent`) plus compatibility aliases and shell payload ambiguity guard.
- Capabilities doc now reflects queue/command surface and canonical-vs-compat callable schema.
- Shared action-lane prompt schema now uses `params` and optional `intent`, while explicitly preserving alias compatibility guidance.

## Status

Closed 2026-04-24.
