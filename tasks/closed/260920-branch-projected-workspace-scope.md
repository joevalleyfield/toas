Filed as: 260920-branch-projected-workspace-scope
FKA:
AKA: branch-local workspace roots; lcp workspace reducer; workspace scope provenance
Legacy index:

keywords: runtime, implementation, active, transcript, policy, lineage, workspace, execution

Parent: `260920-branch-projected-policy-program`
Depends on: `260920-branch-projected-command-context`
Related: `260920-transcript-control-state-contract`; `260919-transcript-env-runtime-fences`

# Project Workspace Scope From the Transcript Branch

Make visible `/workspace` declarations determine the workspace mode and roots
for the current transcript branch and executable frontier, without inheriting
unrelated sibling scope records.

## Current Reality

`/workspace add|remove|reset|mode` emits a whole `workspace_scope` snapshot.
The current reducer scans the journal, so a scope change can leak across
siblings and an inserted declaration cannot govern a same-step restep.

## Desired Reality

On a rewrite, start from the process workspace baseline and reduce direct
workspace declarations in transcript order before the frontier. Add/remove
operate on that branch state; reset restores the process baseline; mode is an
independent replacement. Direct command-context projection may then validate
`/cd` against that same resolved scope.

## Acceptance Criteria

- An inserted `/workspace add PATH` makes a previously out-of-root `/cd PATH`
  usable before an assistant restep.
- A sibling that omits the addition remains restricted.
- Ordered add/remove/reset/mode declarations resolve deterministically.
- Persisted workspace-scope records link to their source message.
- Invalid paths leave branch scope unchanged; ordinary append compatibility is
  explicit until unlinked records age out through rotation.

## Allowed Write Surfaces

- `src/toas/runtime/step_runtime.py`
- `src/toas/runtime/session_step_edges.py`
- `src/toas/graph.py` and `src/toas/graph_record_writers.py`
- focused runtime, graph, and integration tests
- this task, its parent task, and generated `tasks/WORKBOARD.md`

## Exclusions

- Surface selection, session path, managed-backend cwd, and one-shot
  `--control` disposition.
- External workspace discovery or configuration-load reconstitution.

Status: Complete.

## Result

- Rewrites reduce direct `/workspace add|remove|reset|mode` declarations over
  the process baseline before the frontier.
- The resolved roots/mode feed branch-local `/cd` validation, allowing an
  inserted workspace addition to authorize a same-step assistant restep while
  leaving a sibling restricted.
- New `workspace_scope` records link to their source message.
- Verified: 132 focused tests, strict 100% `step_runtime` coverage (120
  targeted tests), Ruff, and full suite (3,260 passed, 17 deselected, 100%
  coverage).
