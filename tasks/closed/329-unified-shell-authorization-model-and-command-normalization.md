## Goal

Create a single shell authorization/evaluation gateway used by assistant tool-calls, compact command proposals, and user-staged executable blocks.

## Why Now

Current behavior still has context/shape friction (`operation` form vs bounded shell checks vs user execution path). We need one model with explicit context policy.

## Scope

- normalize all shell-capable proposal shapes into one internal shell op model
- support compact `command` as sugar for shell execution shape
- ensure consistent feature handling (pipes, heredocs, multiline)
- keep context policy explicit:
  - assistant context: policy-gated
  - user context: always allowed

## Intended Behavior

- equivalent commands have equivalent authorization outcomes regardless of proposal syntax
- blocked assistant execution reports actionable override path
- user execution never blocked by shell policy

## Constraints

- no duplicate authorization implementations in separate paths
- preserve existing durable tool request/result record shape where possible

## Done When

- a single authorization function/path is used by all shell execution entry points
- compact `command` executes with the same evaluator and records as structured shell operations
- tests cover parity across entry shapes and context modes
