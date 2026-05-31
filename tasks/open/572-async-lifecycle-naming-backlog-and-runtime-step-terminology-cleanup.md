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

## Inventory Snapshot (2026-05-30)

This inventory captures current "who does what where" so naming changes can follow ownership reality instead of historical placement.

### 1) Command-Surface Naming (`cli` / `daemon` / `host`)

- `toas step` / `toas watch` / `toas cancel` command entry surfaces are CLI-owned dispatch concerns.
  - `src/toas/cli.py`
  - `src/toas/cli_dispatch.py`
  - `src/toas/cli_async_commands.py`
- `toas daemon [start|stop|status]` currently names RPC server lifecycle, not async execution ownership.
  - `src/toas/cli_runtime_commands.py`
  - `src/toas/daemon/server_lifecycle.py`
- `toas host [serve|stop]` currently names session-owned stdio transport host lifecycle.
  - `src/toas/cli_host_commands.py`
  - `src/toas/runtime/session_host_process.py`
  - `src/toas/runtime/session_host_state.py`

Classification:
- `daemon` command label family: `rename with seam` (touches compatibility and operator vocabulary).
- `host` command label family: `rename now` for docs clarifications, `rename with seam` for CLI verb changes.
- `cli` naming: `keep` (ownership is accurate).

### 2) Async Activity Ownership (`async` / `run_store` / `runtime`)

- Canonical async activity APIs are runtime-owned at the call boundary.
  - `src/toas/runtime/async_activity_store_api.py`
- Backing store still delegates to daemon module path.
  - `src/toas/runtime/async_activity_store.py` (imports `toas.daemon.run_store`)
  - `src/toas/daemon/run_store.py`
- Envelope/status shaping already has runtime naming.
  - `src/toas/runtime/async_lifecycle_envelope_adapter.py`
  - `src/toas/runtime/watch_envelope_adapter.py`

Classification:
- `daemon/run_store.py` placement/name: `rename with seam` (structural move likely needed).
- `runtime/async_activity_store_api.py`: `keep`.
- `runtime/async_activity_store.py` as compatibility bridge: `defer` rename until backing-store extraction slice is active.

### 3) Async Execution Path (`daemon/async_runner.py` vs local/runtime seams)

- Async step execution still routes through daemon-named runner/facades in several paths.
  - `src/toas/daemon/async_runner.py`
  - `src/toas/daemon/facade_async_ops.py`
  - `src/toas/daemon/handlers.py`
- CLI async local path already imports runtime API surfaces for watch/cancel.
  - `src/toas/cli_async_commands.py`

Classification:
- `daemon async` symbol family (`async_runner`, related helper names): `rename with seam`.
- Immediate comment/doc clarifications around "daemon compatibility lane vs runtime ownership": `rename now`.

### 4) Runtime Step Semantics (`step` / `runtime_step`)

- Core step semantics are runtime-owned.
  - `src/toas/runtime/step_runtime.py`
  - `src/toas/step.py` (operator-facing orchestration and command handling)
- Historic names like `run_step_local` remain in compatibility seams and task language.
  - `src/toas/cli.py`
  - references in open/closed tasks and roadmap entries

Classification:
- `run_step_local` and adjacent seam labels: `rename with seam`.
- New docs/task prose should prefer `runtime_step` ownership language now: `rename now`.

## Path Forward (Phased)

1. Phase A: Naming Ledger And Guardrails (`rename now`)
- Add a short glossary note defining `daemon` (transport process), `host` (stdio carrier/session owner), `runtime` (semantic execution), `cli` (surface), `async` (execution mode).
- Update active task/docs prose to use `runtime_step` and "daemon compatibility lane" terminology consistently.
- No symbol/file renames in this phase.

2. Phase B: Seam-First Rehome Slices (`rename with seam`)
- Extract backing async store implementation out of `daemon/run_store.py` into runtime-owned module boundary, leave adapter imports for compatibility.
- Split `daemon/async_runner.py` responsibilities into runtime-owned execution helpers plus transport-facing adapter layer.
- Keep CLI verbs stable during seam extraction; add explicit migration notes.

3. Phase C: External Surface Convergence
- Evaluate CLI vocabulary migration (`daemon` vs `service`/`transport`, `host` verb clarity) only after seam extraction is stable and measured.
- If CLI rename proceeds, ship with compatibility aliases and deprecation timeline.

## Progress Log

- 2026-05-30: Added first full inventory and classification matrix covering command surfaces, async activity ownership, async execution path seams, and runtime step terminology. Established phased path-forward separating doc-language cleanup from structural moves.
- 2026-05-30: Phase A started (docs-only): added terminology guardrails clarifying `cli`/`runtime`/`host`/`daemon`/`async` semantics in `docs/capabilities.md`, including explicit daemon-as-compatibility-transport wording.
