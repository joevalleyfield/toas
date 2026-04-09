## Goal

Refactor tool result projection so transcript/event presentation is not centralized in a large conditional block, and instead follows explicit renderer/translator boundaries.

## Why Now

Current projection logic is concentrated in a large `if` chain, making it harder to evolve tool outputs, keep formatting consistent, and reason about where presentation policy lives.

## Scope

- identify current centralized tool-result projection path
- replace large conditional projection logic with one of:
  - per-tool renderer interface implementation, or
  - parallel projection helper registry keyed by tool/operation
- define boundary between:
  - canonical tool result payload (durable data)
  - transcript-facing rendered output (presentation)
  - event-log serialization policy (if distinct)
- ensure additive path for new tools without expanding a central branching block

## Intended Design Direction

- keep canonical tool result payloads structured and stable
- route rendering through explicit dispatch:
  - `render_tool_result_for_transcript(tool_name, payload)`
  - `render_tool_result_for_event(tool_name, payload)` (if needed)
- prefer deterministic, testable renderers with minimal hidden formatting logic

## Intended Inputs

- `src/toas/step.py`
- `src/toas/tools.py`
- `src/toas/graph.py`
- existing projection helpers and transcript serialization paths
- tests covering tool execution and transcript projection

## Intended Outputs

- cleaner separation of tool execution from tool output presentation
- easier extension for new tools with localized projection code
- reduced risk of regressions from editing one large condition block

## Constraints

- preserve current user-visible output contracts unless intentionally changed
- preserve durable history invariants and append-only behavior
- keep local/RPC projection parity

## Non-Goals

- no redesign of tool payload schema in first pass unless required
- no broad rewrite of unrelated step/orchestration logic

## Done When

- centralized large `if` projection path is removed or reduced to thin dispatch
- renderer/translator strategy is implemented and covered by tests
- adding a new tool projection requires only local registration/implementation
- docs or developer notes explain where projection policy now lives
