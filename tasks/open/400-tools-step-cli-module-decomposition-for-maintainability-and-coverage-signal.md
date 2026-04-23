## Goal

Break up `tools.py`, `step.py`, `cli.py`, and `daemon.py` into smaller modules/directories so coverage reports and maintenance work target coherent units instead of god-module-adjacent files.

## Why Now

Recent coverage gains still leave large uncovered-line lists in each file, which reflects module size/coupling more than isolated behavior gaps. Decomposition will improve both engineering clarity and coverage signal quality.

## Scope

- define decomposition boundaries and target package shapes for:
  - `src/toas/tools.py`
  - `src/toas/step.py`
  - `src/toas/cli.py`
  - `src/toas/daemon.py`
- prioritize extraction of cohesive clusters (parsing, execution routing, render/format helpers, command handlers)
- preserve existing public CLI/API surfaces during extraction
- land in incremental slices with tests guarding behavioral parity

## Breadth-First Master Plan

Phase 0: Boundary Freeze + Compatibility Seams
- add import-stable compatibility wrappers where needed before movement
- document current public entry points that must remain stable
- lock high-risk behavior with golden/contract tests before extraction

Phase 1: Shared Runtime Edges (cross-cutting first)
- extract shared runtime helpers used by multiple modules:
  - rpc gating/wrapping helpers
  - result rendering/format helpers
  - shell/workspace/config policy resolution helpers
- target: reduce duplication before moving larger command/handler clusters

Phase 2: Command/Handler Decomposition
- `cli.py` target package shape:
  - `src/toas/cli/main.py` (argv dispatch only)
  - `src/toas/cli/commands/session.py` (`step`, `watch`, `cancel`)
  - `src/toas/cli/commands/history.py` (`heads`, `history`, `transcript`, `llm-input`, `rebuild`)
  - `src/toas/cli/commands/runtime.py` (`daemon`, `backend`, rpc lifecycle)
  - `src/toas/cli/rendering.py` (stdout/session formatting helpers)
- `daemon.py` target package shape:
  - `src/toas/daemon/server.py` (transport-facing server lifecycle)
  - `src/toas/daemon/handlers.py` (op handlers: step/watch/cancel/backend)
  - `src/toas/daemon/run_store.py` (run state and offsets/seq bookkeeping)
  - `src/toas/daemon/lanes.py` (lane fallback and execution routing)
  - `src/toas/daemon/backend_lifecycle.py` (managed-local backend lifecycle)

Phase 3: Operator/Tool Decomposition
- `step.py` target package shape:
  - `src/toas/runtime/step_runtime.py` (top-level orchestration)
  - `src/toas/runtime/frontier_resolution.py` (frontier extraction and consequence routing)
  - `src/toas/runtime/operator_commands.py` (`/prompt`, `/config`, `/shell`, `/extract`, `/replay`)
  - `src/toas/runtime/projection.py` (outline/compact/render helper surfaces)
- `tools.py` target package shape:
  - `src/toas/tools/registry.py` (`Tool`, registry, validate/dispatch)
  - `src/toas/tools/file_ops.py` (read/write/replace/apply_patch family)
  - `src/toas/tools/shell_ops.py` (`shell`, `shell_script`, user-shell adapters)
  - `src/toas/tools/capability_help.py` (topic resolution/details/examples)
  - `src/toas/tools/rendering.py` (tool result shaping/render helpers)

Phase 4: Coverage Signal Cleanup
- retire compatibility shims where safe
- update tests/imports to target new module boundaries directly
- set next ratchet targets per new focused modules instead of monolith files

## Task Slicing Rules

- each extraction slice must:
  - move one cohesive cluster only
  - include behavior-locking tests in the same commit
  - leave legacy import surface intact until callers are migrated
- each phase should open concrete subtasks with:
  - target files/modules
  - compatibility contract
  - explicit rollback plan if behavior drift is detected

## Intended Behavior

- smaller, focused modules with explicit ownership boundaries
- reduced cross-cutting helper sprawl in monolithic files
- coverage reports that more clearly identify true behavior gaps

## Constraints

- no semantic drift in transcript/history/runtime contracts
- no big-bang rename; extract in staged commits with compatibility imports where needed
- keep task/roadmap stitching current as each decomposition slice lands

## Done When

- at least first decomposition slices land for all four targets
- new module boundaries are documented and adopted by tests
- follow-on coverage tasks can target focused modules instead of monolithic files

## Subtasks

- `401`: phase-0 boundary freeze and compatibility seam locks for `tools.py`/`step.py`/`cli.py`/`daemon.py`
- `402`: phase-1 shared runtime edge extraction (RPC wrapping, result rendering helpers, policy resolution)
- `403`: phase-2 `cli`/`daemon` command-handler decomposition (transport/handler/run-store splits)
- `404`: phase-3 `step`/`tools` decomposition bootstrap (runtime/operator/tool registry and cohesive operation modules)
- `421`: step operator-command extraction (`_execute_operator_command`) into `runtime/operator_commands.py` boundary
- `422`: step top-level orchestration extraction (`step` flow + consequence stitching) into `runtime/step_runtime.py`
- `423`: CLI generation/session command extraction (`_GenerationRunner` + `run_step_local`) into `cli/commands/session.py` boundary
- `424`: tools text-rewrite extraction (`replace_range`/`replace_block` family) into `tools_cluster/file_ops.py`
- `425`: daemon package-facade reduction (`daemon/__init__.py`) by moving server/bootstrap wiring to focused modules
- `426`: runtime operator-command family decomposition (`execute_operator_command`) into focused per-family handlers
- `427`: CLI session assembly and side-effects extraction (`_stitch_frontier_records`, `_apply_result_side_effects`) into focused modules
- `428`: CLI main/dispatch surface decomposition (`main` routing + command map) into focused dispatch module(s)
- `429`: tools apply_patch and code_survey extraction from `tools.py` into `tools_cluster` modules
- `430`: daemon facade thinning second pass (`daemon/__init__.py`) to move remaining non-trivial lifecycle/wrapper logic
- `431`: runtime config/help handler decomposition (`handle_config_help_commands`) into smaller focused helpers
- `432`: runtime prompt/workspace handler decomposition (`handle_prompt_workspace_commands`) into smaller focused helpers
- `433`: runtime extract/replay handler decomposition plus one bounded `run_step` seam extraction

## Progress

- `421`-`425` completed and moved to `tasks/closed/` with parity-verified extraction commits and full-suite validation
- follow-on decomposition queue opened from post-`425` `code_survey`: `426`-`430`
- `426` completed and moved to `tasks/closed/` after splitting `runtime/operator_commands.py` into command-family handler modules plus direct handler tests
- `427` completed and moved to `tasks/closed/` after extracting CLI session assembly/side-effect helper cluster into `runtime/session_step_edges.py` with direct module tests and parity validation
- `428` completed and moved to `tasks/closed/` after extracting CLI `main` dispatch parsing/routing into `cli_dispatch.py` with direct dispatch tests and parity validation
- `429` completed and moved to `tasks/closed/` after extracting `apply_patch` and `code_survey` internals from `tools.py` into `tools_cluster` modules with direct module tests
- `430` completed and moved to `tasks/closed/` after extracting daemon facade helper/process clusters into focused `daemon` package modules (`facade_helpers`, `facade_process`) with compatibility wrappers retained in `daemon/__init__.py` and full-suite parity validation
- post-`430` `code_survey` triage opened next decomposition queue: `431`-`433` (largest remaining function-level hotspots in runtime command handlers/orchestration)
- `431` completed and moved to `tasks/closed/` after decomposing `handle_config_help_commands` into focused helper units (show/secret/set/backend/unset/restore/load/save/help) with thin command dispatch and added helper-branch tests
- `432` completed and moved to `tasks/closed/` after decomposing `handle_prompt_workspace_commands` into per-command helpers (prompts/prompt/backend/model/env/shell/pwd/cd/workspace/outline/compact) with added helper-path tests for compact/cd parsing seams
- `433` completed and moved to `tasks/closed/` after decomposing `handle_extract_replay_commands` into parser/collector/renderer/execution helpers and extracting bounded `run_step` helper seams (`_resolve_execution_dependencies`, `_collect_frontier_intents`) with direct helper tests
