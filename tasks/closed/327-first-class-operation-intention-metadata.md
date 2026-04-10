## Goal

Introduce first-class `intention` metadata on tool operations so each executable action can carry explicit rationale, while keeping `operation` authoritative for execution semantics.

## Why Now

Models frequently emit multiple YAML blocks to preserve per-step intent. A per-operation `intention` field captures that rationale directly in the structured lane without requiring fragmented call shapes.

## Scope

- support optional `intention` on:
  - single operation object
  - each item in operation list/tool plan
- preserve existing operation execution behavior:
  - `operation` + `arguments` remain authoritative
  - `intention` is metadata, not executable authority
- surface `intention` in:
  - extraction/previews
  - tool request/result rendering where useful
  - durable request payloads
- optionally warn (not block by default) on obvious intention/operation mismatch

## Intended Behavior

- existing plans without `intention` keep working unchanged
- plans with `intention` provide clearer operator context
- replay/history retains both:
  - what was done (`operation`)
  - why (`intention`)

## Intended Inputs

- `src/toas/graph.py` (plan normalization / durable payloads)
- `src/toas/step.py` (extraction and previews)
- `src/toas/tools.py` (result shaping paths where relevant)
- tests for normalization, execution, and rendering paths
- docs/help updates

## Intended Outputs

- clearer structured-action traceability
- reduced need for fragmented multi-block proposals
- better alignment with transcript compression of action + rationale

## Constraints

- backward compatibility with current callable YAML
- operation must remain required and authoritative
- no hidden execution semantics tied to free-form intention text

## Non-Goals

- no intention-only executable actions
- no mandatory intention requirement in first pass

## Done When

- normalization accepts and preserves optional `intention`
- execution path ignores `intention` for authority but carries it in records
- previews/rendering can display intention context
- tests cover single-call and multi-call intention flows
