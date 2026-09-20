Filed as: 260920-branch-projected-command-context
FKA:
AKA: branch-local cwd; lcp cd reducer; command context provenance
Legacy index:

keywords: runtime, implementation, active, transcript, policy, lineage, execution, workspace

Parent: `260920-branch-projected-policy-program`
Depends on: `260920-lcp-direct-policy-deltas`
Related: `260920-one-shot-control-ingress-disposition`; `260919-transcript-env-runtime-fences`

# Project Command Context From the Transcript Branch

Make ordered direct `/cd` declarations select the working directory for the
current transcript branch and its executable frontier, without widening this
slice into workspace-root policy.

Status: Complete.

## Current Reality

`/cd` emits a `command_context` record after its result is persisted.
`active_command_context(events)` scans journal order, and runtime context uses
that history-wide result before reconciliation. A recreated or inserted `/cd`
therefore cannot reliably apply to a same-step assistant restep, while an
unrelated sibling may inherit it.

## Desired Reality

The command directory for an operation equals the baseline command context
plus visible direct `/cd PATH` declarations before that operation in the
selected reconstructed transcript. `/cd -` uses the immediately preceding
visible command directory. A sibling without the declaration does not inherit
it.

## Scope

- Reduce valid direct `/cd PATH` and `/cd -` declarations in transcript order
  before the frontier.
- Feed the resulting cwd/previous-cwd to executable plans and command handlers
  during the same step.
- Add source-message linkage to newly persisted `command_context` records.
- Preserve path validation and workspace-mode behavior already owned by the
  command handler.

## Exclusions

- `/workspace` roots/mode, surface selection, session paths, and managed
  backend cwd.
- One-shot `--control` semantics and external configuration loading.
- Changing filesystem permissions or reinterpreting arbitrary shell `cd`.

## Acceptance Criteria

- Inserting a valid `/cd` before an unchanged assistant executable plan makes
  that plan run from the new directory.
- The same plan on a sibling without the declaration uses its own baseline
  directory.
- Ordered `/cd one`, `/cd -` resolves to the prior visible directory.
- A new command-context record links to the source message that authored it.
- Invalid/missing directories retain the current error behavior and do not
  silently change the execution cwd.

## Allowed Write Surfaces

- `src/toas/runtime/step_runtime.py`
- `src/toas/runtime/session_step_edges.py`
- `src/toas/graph.py` and `src/toas/graph_record_writers.py`
- focused runtime, graph, and policy-reinterpretation tests
- this task, its parent task, and generated `tasks/WORKBOARD.md`

## Completion Evidence

- Focused command-context/restep and persistence tests pass.
- The policy-runtime targeted coverage gate remains at 100%.
- Full suite and Ruff pass before closure.

## Result

- The step boundary reduces valid direct `/cd` declarations before the frontier
  over the process baseline on a rewrite, rather than inheriting an unrelated
  journal context.
- Inserted `/cd` now changes same-step assistant-restep execution; a sibling
  that omits it uses its own baseline cwd.
- Ordered declarations, `/cd -`, malformed input, and invalid targets are
  covered. Invalid declarations leave the current cwd unchanged.
- Persisted `command_context` records now identify their source message.
- Verified: 129 focused tests, strict 100% `step_runtime` coverage (119
  targeted tests), Ruff, and full suite (3,257 passed, 17 deselected, 100%
  coverage).
