## Goal

Provide historical callable replay as a separate, explicitly named command so replay power is available without overloading `/extract`.

## Why Now

Historical replay can be useful, but bundling it under `/extract` obscures intent and caused operator-model drift. Keeping replay explicit preserves clarity.

## Scope

- introduce a distinct replay command (name TBD, e.g. `/replay`)
- replay command may support index/selection over prior callable messages
- preserve existing duplicate-execution safeguards and `--force` semantics
- keep durable `tool_request` / `tool_result` linkage to replay target message
- update docs/help to distinguish:
  - `/extract` = frontier assistant adoption
  - replay command = historical invocation

## Intended Inputs

- current historical selection/execution behavior in `/extract`
- tool record write semantics in `cli.py`
- lineage helpers in `graph.py`

## Intended Outputs

- explicit replay command with clear invocation semantics
- replay tests independent from `/extract` tests
- reduced ambiguity in operator command language

## Constraints

- no hidden replay behavior in `/extract`
- replay remains mechanical and deterministic
- durable history invariants unchanged

## Non-Goals

- no LLM-assisted target selection
- no semantic grouping/ranking of replay candidates

## Done When

- historical replay is available only via the explicit replay command
- `/extract` no longer exposes historical index scanning
- docs and tests clearly separate the two concepts
