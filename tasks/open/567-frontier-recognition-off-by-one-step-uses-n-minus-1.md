# 567: Frontier Recognition Off-by-One (`step` Uses `n-1` Instead of `n`)

## Why

Frontier recognition appears to be off by one, where `toas step` operates from `n-1` instead of the true frontier `n`. This violates expected lineage/continuation behavior and should not be possible under current invariants.

## Goal

Ensure frontier detection and `step` execution always use the actual frontier head/event (`n`), never the prior one (`n-1`), unless an explicit user selection routes execution elsewhere.

## Scope

- Reproduce the off-by-one case with a deterministic fixture or transcript history.
- Trace frontier/head resolution path used by `toas step`.
- Fix indexing/selection logic so implicit `step` always binds to the true frontier.
- Verify behavior across local (`TOAS_RPC_MODE=off`) and routed (`auto`/`on`) execution paths where applicable.
- Add regression tests covering frontier recognition and step execution parentage.

## Reproduction Strategy

Initial broad matrix did not isolate a single trigger, but targeted transcript-tail mutation runs now provide a deterministic drift signature.

### 1) Build a mode/transport matrix

Run the same minimal transcript-edit + `step` sequence across:

- Host path active (local host attached)
- Host path inactive (CLI-only / no host coupling)
- `TOAS_RPC_MODE=off`
- `TOAS_RPC_MODE=auto`
- `TOAS_RPC_MODE=on`

Primary question: does the first divergence appear only with host involvement, or under pure local mode as well?

### 2) Use a minimal deterministic sequence

For each matrix cell:

- Start from a clean temporary workspace/session artifact.
- Append exactly one user message to transcript.
- Run `toas step`.
- Record reported/selected head before step and after step.
- Repeat for 3-5 iterations, one append + one step each iteration.

Expected invariant each iteration: consequence should attach to current frontier (`n`), never prior frontier (`n-1`).

### 3) Capture first failing transition

On first observed failure, preserve:

- `session.md` at failure moment
- `events.jsonl`
- `toas heads`
- `toas history 30`
- `toas transcript`
- active mode/env (`TOAS_RPC_MODE`, host attach state)

Do not continue mutating the same artifact after first failure; copy it for forensic replay.

### 4) Reduce to deterministic fixture

Convert captured failing artifact into a regression fixture/test that:

- reconstructs frontier state
- executes one `step`
- asserts selected parent/head equals true frontier pre-step

## Deterministic Repro Recipe (Current Best)

Use frontier debug instrumentation (`TOAS_DEBUG_FRONTIER=1`) and run transcript-tail mutation sequences in a clean temp workspace.

### Command Harness

Reference artifact run:

- `/tmp/toas-frontier-targeted-20260525-093658`

Executed cases:

- `result_tail_edit`
- `user_tail_edit`
- `truncate_rebuild_with_result`

### Trigger Shape

Across cases, after several `step` runs:

- durable tip continues advancing (`bind_parent` increments)
- transcript reconciliation remains pinned to older boundary (`lcp_index` unchanged at small index, commonly `3`)
- `divergence_parent` remains stale (for example `n2`) while storage tip is newer (`n5`, `n7`, ...)

Strongest collapse observed in `truncate_rebuild_with_result`:

- `lcp_index` drops to `1`
- `divergence_parent` resets near root (`n0`)
- `bind_parent` remains advanced (`n7`)

This is a concrete state-space mismatch between durable frontier and transcript alignment frontier.

### Debug Signatures To Assert

Treat any of the following as repro-positive:

- `build_new_transcript_nodes.bind_parent != build_new_transcript_nodes.divergence_parent` for repeated steps while transcript tail is being edited
- `run_step_frontier.frontier_id` or preview indicating older boundary reuse despite increasing `bind_parent`
- sudden `lcp_index` collapse (example: `3 -> 1`) after tail truncate/rebuild

## Possible Regression Ancestry

This behavior may be related to prior parent-selection / root-divergence work:

- Open: [549](/Users/tim/Documents/Projects/toas/tasks/open/549-lcp-root-class-relinearization-hardening.md)
- Closed: [550](/Users/tim/Documents/Projects/toas/tasks/closed/550-root-sentinel-taxonomy-unification.md)

No causality claim yet; keep this as a focused audit lead during fix design.

### Suggested Transition Log Template

- iteration index
- transcript append summary
- pre-step selected head
- pre-step computed frontier
- post-step new records summary
- observed parent linkage
- pass/fail (n vs n-1)

## Non-Goals

- Changing branching semantics for explicit non-tip continuation.
- Broad redesign of history projection or transcript format.
