## Goal

Replace "$ + trailing-lines" multiline execution with tail-armed execution of the same structured command shape used in assistant proposals, so multiline commands preserve shape with no conversion.

## Why Now

Current multiline user-shell behavior executes all lines after a `$ ...` starter inside a user message. That is ambiguous and diverges from the intended model: preserved structured command blocks, armed by user-tail placement.

## Scope

- keep single-line `$ ...` execution unchanged
- support user-tail structured command execution from tail YAML block shape:
  - ```yaml\ncommand: ...\n```
  - ```yaml\ncmd: ...\n```
- execute only the selected tail command shape (not arbitrary trailing prose)
- align durability tool_request/tool_result detection with the same tail-armed structured shape

## Intended Inputs

- command extraction and execution selection in `src/toas/step.py`
- user-shell plan detection in `src/toas/graph.py`
- step durability wiring in `src/toas/cli.py`
- tests in `tests/test_step.py` and `tests/test_graph.py`

## Intended Outputs

- multiline execution path uses preserved structured shape directly
- no implicit “run everything after `$`” behavior
- tail-only arming semantics for structured user command blocks

## Constraints

- no hidden quote/syntax rewriting
- no by-reference execution indirection
- preserve bounded model-addressable `shell` tool policy split from user-unbounded intent

## Non-Goals

- no non-tail runnable-block policy in this task
- no new block marker syntax

## Done When

- user-tail YAML `command`/`cmd` blocks execute as explicit user intent
- multiline `$` starter no longer implies trailing-line command body execution
- single-line `$ ...` execution remains intact
- durability and tests reflect the new selection contract
