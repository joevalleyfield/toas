# 572: Async Lifecycle Naming Backlog And runtime_step Terminology Cleanup

## Goal

Track and systematically retire ambiguous naming around async lifecycle/runtime surfaces, starting with the `daemon async` misnomer and adjacent boundary-confusing terms.

## Why

Current naming leaks older architecture boundaries:
- `daemon async` names are used in paths now shared by local/runtime-host/daemon-compatible lanes.
- CLI/runtime layering work (including `runtime_step` seam extraction) exposes naming that no longer matches ownership.

This slows protocol work and increases cognitive overhead when reasoning about lane/phase semantics.

## Scope

- Inventory naming hotspots where ownership/semantics are ambiguous.
- Classify each hotspot as:
  - `rename now` (low-risk, local)
  - `rename with seam` (must move with structural refactor)
  - `defer` (high churn/risk)
- Land no-op or near-no-op naming/doc updates where safe.
- Produce a prioritized rename plan for follow-on refactor slices.

## Initial Candidates

1. `daemon async` naming cluster
   - `src/toas/daemon/async_runner.py`
   - `src/toas/daemon/run_store.py`
   - `src/toas/cli_async_commands.py`
   - Related docs/tests references
2. `operator` polysemy hotspots
   - User meaning vs runtime meaning vs command-plane meaning in docs/comments/task language
3. `run_step_local` CLI/runtime seam naming
   - Terms that should converge on `runtime_step` for semantic callback ownership

## Non-Goals

- Large mechanical renames without boundary validation.
- Behavior changes unrelated to naming/ownership clarity.

## Done When

- A documented naming inventory exists with action classification (`rename now` / `rename with seam` / `defer`).
- At least one high-confidence misleading label family (starting with `daemon async`) has a concrete rename proposal and migration notes.
- `runtime_step` terminology is used consistently in new seam/refactor docs for semantic callback ownership.
- Follow-on tasks (if needed) are opened with explicit scope so cleanup does not get lost.

## Notes

- This backlog task is intentionally parallel to `571` and should absorb additional naming confusion discovered during wire-contract and lane/phase work.
