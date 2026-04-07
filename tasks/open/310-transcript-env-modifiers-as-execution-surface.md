## Goal

Add transcript-scoped environment modifiers so effective execution env is projected from transcript intent (with clear precedence), not hidden mutable global state.

## Why Now

Operators currently rely on Vim/process env for CLI fallback and lack a transcript-native way to express env intent that branches/replays predictably. This is the next execution-surface seam after cwd.

## Scope

- add transcript commands for env modifiers (initial shape):
  - `/env set <KEY> <VALUE>`
  - `/env unset <KEY>`
  - `/env` (show effective env modifiers in scope)
- resolve effective env during step execution from:
  - operator/runtime base env
  - transcript modifiers in order (set/unset)
- apply resolved env to execution consumers (user shell path and relevant tool execution paths)
- include resolved env in RPC request context as execution surface data (not ad-hoc daemon state mutation)

## Intended Inputs

- slash-command handling in `src/toas/step.py`
- CLI/RPC request construction in `src/toas/cli.py`
- daemon request execution context in `src/toas/daemon.py` / rpc transport path
- history/projection behavior in `src/toas/graph.py` and transcript handling

## Intended Outputs

- first-class transcript env modifier workflow
- deterministic env projection for execution
- branch/replay behavior aligned with transcript-derived state

## Constraints

- no secret-value durability policy changes in this task (coordinate with existing secret-safe lane)
- no global daemon env mutation side effects
- keep behavior explicit and inspectable

## Non-Goals

- no model selection semantics in this task
- no advanced scoped blocks/namespaces for env modifiers
- no external secret manager integration

## Done When

- operators can set/unset env via transcript commands
- effective env for execution reflects transcript modifiers in order
- RPC path receives/env-applies projected env context
- tests cover set/unset ordering, branch behavior, and CLI-vs-RPC parity
