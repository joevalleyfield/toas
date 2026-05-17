## Goal

Fix append-time parent selection so transcript edits create graph branches instead of linear replay chains.

## Why Now

A minimal deterministic repro shows durable history linearizing when it should branch:

- baseline transcript: `USER A` -> `ASSISTANT B` -> `USER C`
- edit `B` -> `D` in session and step again
- expected: branch from `A` producing `A -> B -> C` and `A -> D -> C'` (two heads)
- observed: new nodes append from storage tip, yielding a single linear chain

This violates core graph semantics and makes `rebuild` look wrong even when projection is faithful.

## Scope

- reproduce and codify the failure as deterministic tests (no model dependency)
- trace parent-assignment path from step reconciliation through message materialization
- enforce explicit parent selection from reconciled lineage boundary (not storage-tip fallback) for append-time writes
- preserve control-record behavior (`head`, `jump`, `anchor`) while fixing default branch behavior
- add diagnostics at write-time for chosen parent/source when debug flags are enabled

## Intended Behavior

- editing prior transcript content creates a branch at the matched ancestor
- unchanged prefix nodes are reused by reference, not rewritten as fresh linear continuation
- resulting durable message graph can have multiple heads when lineage diverges
- `toas heads` and `toas rebuild <head>` reflect branch-correct lineage

## Constraints

- never mutate prior durable events
- no destructive rewrite/migration required for existing logs in this task
- keep transcript projection behavior unchanged (fix source-of-truth writes, not projection cosmetics)

## Done When

- deterministic repro test fails on pre-fix code and passes post-fix
- parent links in durable message events reflect branch parentage in edited-transcript scenario
- `heads` output shows expected multiple heads for the repro
- docs/notes capture write-time parent selection invariant and debug procedure

## Initial Repro (2026-05-17)

Observed in `/tmp/toas-branch-repro.q6hO6t`:

- message chain became linear: `... n4(C) -> n5(D) -> n6(A) -> n7(D) -> n8(C) -> n9(D)`
- only one head (`n9`) instead of branch heads
- confirms parent selection is currently tip-biased in this path

## Progress

- fixed divergence-parent selection in `runtime/step_runtime._build_new_transcript_nodes` so first appended node uses the matched boundary parent (`bound_lineage[i-1].id`) instead of falling back to selected-tip behavior
- carried message ids through step-local projected `log` entries in `cli_session_commands._build_runtime_context` so boundary-parent resolution is available in full `run_step_local` flow
- added seam regression coverage for divergence-parent behavior:
  - `tests/test_runtime_step_runtime.py::test_build_new_transcript_nodes_sets_parent_to_divergence_boundary_not_tip`
- added end-to-end deterministic branch regression coverage:
  - `tests/test_cli.py::test_run_step_local_transcript_edit_branches_from_divergence_boundary`
- adjusted existing CLI `fake_step` expectations to accept id-carrying projected log entries now intentionally passed through step-local runtime context

## Remaining

- extend deterministic coverage to additional branch shapes (assistant-only divergence, multi-turn post-divergence tails, and bind-index constrained divergence)
- consider a dedicated projection/append diagnostic command to visualize boundary parent choice during step for operator debugging
