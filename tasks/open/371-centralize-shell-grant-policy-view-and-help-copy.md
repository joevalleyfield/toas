## Goal

Centralize shell grant rendering and help/usage copy so policy semantics and operator guidance stay consistent across command surfaces.

## Why Now

`330` landed the grant model, but policy display/copy is still spread across `step.py`, config display snippets, and shell command usage strings. Drift risk is now the main reliability risk in this area.

## Scope

- extract one shared renderer for:
  - effective grants with source attribution
  - transcript-lane delta (added/removed)
  - config baseline summary
- extract one shared source for `/shell` usage/help copy
- route `/shell list` and related result text through shared helpers
- keep existing behavior and wording intent, but remove duplicated string assembly paths

## Intended Behavior

- one change to grant semantics/copy updates all shell policy-facing surfaces
- `/shell` output remains compact, operator-readable, and deterministic
- tests fail fast on rendering/copy drift

## Constraints

- no policy behavior change in this task
- no hidden mutable state
- preserve transcript/config lane semantics from `330`

## Done When

- duplicate shell policy rendering/copy blocks are removed from command handlers
- shared helper(s) are unit-tested
- existing `/shell` behavior tests remain green with minimal fixture churn
