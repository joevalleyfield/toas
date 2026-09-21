Filed as: 260920-config-load-result-reconstitution
FKA:
AKA: immutable config-load result; branch load replay; identified external resolution
Legacy index:

keywords: runtime, implementation, historical, correctness, transcript, policy, lineage, config, provenance, replay

Parent: `260920-branch-projected-policy-program`
Depends on: `260920-lcp-direct-policy-deltas`
Related: `325-config-override-lifecycle-load-save-restore-and-unset`; `260920-one-shot-control-ingress-disposition`

# Reconstitute Config Loads From Immutable Identified Results

Allow a recreated `/config load` control on a transcript branch to reuse its
prior resolved delta only through an immutable, source-linked result record,
without silently rereading external file state.

## Current Reality

`/config load PATH` immediately reads a file and emits a generic
`config_update`. The Phase-1 direct reducer deliberately excludes loads, so a
rewritten branch cannot apply the old result from transcript text alone. A
fresh reread during reinterpretation would make history depend on mutable
external state.

## Desired Reality

A completed load has a durable typed result containing its source message ID,
canonical resolved delta, input identity/digest, and reconstitution eligibility.
A recreated matching load may refer to that result; an explicit fresh-load form
performs a new read and records a new result. Missing, ambiguous, or changed
references fail visibly rather than guessing.

## Acceptance Criteria

- A file load produces an immutable identified resolution result linked to its
  source message.
- Recreating that source on a branch reuses the recorded canonical delta even
  after the file changes or disappears.
- A sibling without the recreated load does not receive the delta.
- Fresh loading is explicit and records a distinct result.
- Ambiguous/missing result references fail without applying configuration.

## Allowed Write Surfaces

- config command handler and result-node contract
- graph record writers/readers and persistence edges
- `src/toas/runtime/step_runtime.py`
- focused config, graph, and policy-reinterpretation tests
- this task, parent task, and generated workboard

## Exclusions

- General external command replay, endpoint refresh reconstitution, settings
  checkpoints, or broad result-reference syntax beyond config load.
- Treating path strings alone as immutable evidence.

## Progress

- Added source-linked `config_load_resolution` records containing the resolved
  delta, input digest, canonical target path, and reconstitution eligibility.
- Branch projection now applies a load only when exactly one eligible result is
  linked to a prior message with the same `/config load` declaration. It never
  rereads the file during reinterpretation.
- `/config load --fresh [path]` is explicit frontier work. A historical fresh
  declaration cannot silently perform external I/O during a rewrite.
- Missing or ambiguous evidence produces a visible reconstitution error rather
  than applying a guessed delta.

## Completion Evidence

- `./.codex-local/bin/uvt run ruff check .`
- `./.codex-local/bin/uvt run pytest` — 3271 passed, 17 deselected, 100% coverage.

Status: Complete.
