Filed as: 260920-branch-projected-target-selection
FKA:
AKA: branch-local model selection; lcp target reducer; target selection provenance
Legacy index:

keywords: runtime, implementation, active, transcript, policy, lineage, model, target, config

Parent: `260920-branch-projected-policy-program`
Depends on: `260920-lcp-direct-policy-deltas`
Related: `260920-transcript-control-state-contract`; `260920-one-shot-control-ingress-disposition`; `260912-target-basename-from-observed-model`

# Project Active Model Selection From the Transcript Branch

Make direct active-target selection operational under LCP restep and isolated
between sibling transcript branches, without expanding this slice into target
catalog or endpoint-catalog reconstruction.

## Current Reality

`/model select TARGET` produces a `target_selection` durable record. The
record has no source-message linkage and `active_target_selection(events)`
reduces the complete journal in append order. Model invocation therefore sees
the last selection from any branch. The endpoint-bootstrap `--select` path
emits the same record shape.

Direct config/grant declarations already have a Phase-1 branch projection;
active-target selection does not. Target definitions themselves arrive through
specialized `config_update` records and are deliberately outside this initial
selection-only seam.

## Desired Reality

For an operation on a reconstructed transcript branch, the active model target
is the last eligible selection declaration visible before that operation on
that branch, over the ordinary user/workspace baseline target catalog.

An inserted `/model select TARGET_B` before an unchanged assistant operation
can restep it under `TARGET_B`; a sibling which omits that declaration remains
on its own selected target. New durable `target_selection` records identify
the materialized source message.

## Scope

- Add source-message linkage to target-selection records and persistence.
- Reduce direct `/model select TARGET` declarations from the selected working
  transcript through the frontier, then supply the selected target to model
  invocation and relevant operator views.
- Cover exact assistant restep, sibling isolation, and ordinary append
  compatibility.
- Treat a target catalog from files/current baseline as the available catalog.

## Exclusions

- `/config target add|set|remove`, endpoint catalog mutation, model discovery,
  and endpoint bootstrap reconstitution.
- Fresh remote model observation and any external-result reuse.
- One-shot `--control` semantics; see
  `260920-one-shot-control-ingress-disposition`.
- Surface, workspace, command-context, grants, or child-environment reducers.

## Acceptance Criteria

- A pre-existing target catalog with `TARGET_A` and `TARGET_B` supports a
  transcript-inserted `/model select TARGET_B` before an unchanged assistant
  operation; its recorded model invocation resolves `TARGET_B`.
- A sibling restep without the declaration does not inherit `TARGET_B`.
- The emitted `target_selection` record has `related_to` equal to its source
  message ID.
- An ordinary append still honors legacy target-selection records until that
  compatibility input is explicitly retired.
- Invalid/missing targets preserve current validation behavior and do not
  create an effective selection.

## Allowed Write Surfaces

- `src/toas/runtime/step_runtime.py`
- `src/toas/runtime/session_step_edges.py`
- `src/toas/runtime/model_invocation_contracts.py`
- `src/toas/graph.py` and `src/toas/graph_record_writers.py`
- focused runtime, graph, and integration tests
- this task, its parent task, and generated `tasks/WORKBOARD.md`

## Completion Evidence

- Focused target-selection/restep tests and the target-model invocation tests
  pass.
- The policy-runtime targeted coverage gate remains at 100%.
- Full suite, acceptance selection scenario, and Ruff pass before closure.
