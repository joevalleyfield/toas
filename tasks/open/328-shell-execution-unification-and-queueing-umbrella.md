## Goal

Unify shell execution semantics across assistant proposals and user-staged execution, while introducing queue-aware continuation for mixed authorization outcomes.

## Why Now

Shell capability exists in multiple places today (assistant tool-calls, user tail execution, compact command-like forms), but behavior and authorization friction still vary by context and shape. This arc aligns capability, safety, and ergonomics.

## Scope

- establish one internal shell-operation normalization path
- align authorization semantics across all shell entry paths
- add queue/continuation behavior for mixed allow/deny sequences
- support compact and structured proposal forms without semantic drift
- keep user-context execution authoritative and unblockable

## Intended Behavior

- pipes and heredocs work consistently across all shell entry paths
- syntax differences (`operation: shell`, compact command forms, user staged blocks) do not imply different authorization logic
- multi-op sequences run in order with automatic pause/continue at blocked boundaries

## Intended Inputs

- `src/toas/graph.py`
- `src/toas/step.py`
- `src/toas/tools.py`
- `src/toas/transcript.py`
- `README.md` and docs where operator behavior is described

## Intended Outputs

- coherent shell execution and authorization model
- reduced manual extract/re-run loops for mixed-op sequences
- clearer durable traces for queue decisions and continuation

## Constraints

- keep user-context execution as final authority
- no silent policy forks by syntax shape
- preserve existing durable-record invariants

## Non-Goals

- no autonomous user-less execution loop in this arc
- no broad hidden auto-approval semantics

## Done When

- subtasks `329`-`333` are implemented and closed
- behavior parity is test-covered for single-line, multiline, pipe, and heredoc shell flows
