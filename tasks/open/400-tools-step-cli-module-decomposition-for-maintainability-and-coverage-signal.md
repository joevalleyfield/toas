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
- `434`: tools execution/validation boundary extraction from `tools.py` into focused `tools_cluster` module(s)
- `435`: tools capability/help/profile rendering extraction from `tools.py`
- `436`: tools shell boundary + user shell path extraction from `tools.py`

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
- post-`433` reassessment opened next tools-focused decomposition queue: `434`-`436` (execution/validation boundary, capability/help rendering, shell boundary/user-shell extraction)
- `434` completed and moved to `tasks/closed/` after extracting non-shell tool execution/validation operations (`read/write/search/echo_block/get_structure`) from `tools.py` into `tools_cluster/basic_ops.py` with direct module tests
- `435` completed and moved to `tasks/closed/` after extracting capability/help/profile rendering logic from `tools.py` into `tools_cluster/capability_help_ops.py` with direct module tests for topic normalization/selection/detail branches
- `436` completed and moved to `tasks/closed/` after extracting shell boundary and user-shell path logic from `tools.py` into `tools_cluster/shell_ops.py` with compatibility wrappers retained in `tools.py` and direct shell-ops tests
- post-`436` reassessment opened the next decomposition queue focused on remaining high branch-density hotspots: `config` parsing/overrides split, `cli_dispatch` command-routing split, `daemon.async_runner` warm/process split, `tools_cluster.file_ops` matcher/diagnostic split, runtime config-backend shaping split, and a final `step_runtime.run_step` phase split
- config parsing/overrides split landed: `config.py` now delegates parsing/coercion to `config_parsing.py` and nested merge/materialization to `config_overrides.py` with compatibility wrappers retained and full-suite parity validation (`992 passed`)
- CLI dispatch routing split landed: `cli_dispatch.py` now delegates argument parsing branches for `watch`/`prompt`/`ancestry` to `cli_dispatch_ops.py`, reducing branch density in `dispatch_main` while retaining exact command behavior (`995 passed`)
- daemon warm/process split landed: warm in-process execution lifecycle moved from nested closure inside `start_async_step_warm` to `daemon/async_runner_warm.py`, leaving `daemon/async_runner.py` as async orchestration and improving direct seam testability (`997 passed`)
- tools file matcher/diagnostic split landed: `tools_cluster/file_ops.py` now delegates block-pattern selection and mismatch diagnostics to `tools_cluster/file_match_ops.py`, reducing replace operation branch density and isolating matcher-specific tests (`999 passed`)
- runtime config/backend shaping split landed: backend list/add/set/remove/capture logic extracted from `runtime/operator_command_config_help.py` to `runtime/operator_config_backend_ops.py`, making config/help command routing thinner and easier to target in tests (`1001 passed`)
- step runtime phase split landed: `runtime/step_runtime.run_step` now delegates transcript-delta assembly and frontier consequence execution to focused helpers (`_build_new_transcript_nodes`, `_execute_frontier_consequences`) with direct helper coverage and parity (`1003 passed`)
- CLI replay-script flow split landed: `cli.py` now delegates progressive replay execution to `cli_replay_script.run_replay_script_local` via explicit dependency bundle, reducing command-handler density in `cli.py` while preserving CLI surface behavior
- post-455 `code_survey` checkpoint rerun (top functions) highlighted `operator_config_backend_ops.config_backend_result`, `config_parsing.parse_config_value`, and `session_step_edges.apply_result_side_effects` as compact high-leverage decomposition seams under the 400/374 overlap
- latest decomposition pass split `/config backend` handling into focused helper branches in `runtime/operator_config_backend_ops.py` (`list|add|remove|set|capture`), keeping facade dispatch thin and validation paths isolated
- latest decomposition pass split config parsing coercion helpers in `config_parsing.py` (`_parse_choice`, `_parse_int_nonnegative`, `_parse_float_nonnegative`, `_parse_bool`, `_field_default_for_key`) to reduce branch density in `parse_config_value`
- latest decomposition pass split session result side-effects fan-out in `runtime/session_step_edges.py` into focused helpers (`_apply_queue_updates`, `_apply_lens_updates`, `_apply_context_updates`, `_apply_workspace_updates`, `_apply_secret_updates`, `_apply_config_updates`, `_apply_config_saves`, `_apply_session_updates`)
- latest decomposition pass split `runtime/operator_command_prompt_workspace._handle_lens` nested closures into module-level helpers (`_extract_lens_fenced_distillation`, `_parse_lens_source_ids`, `_collect_known_message_ids`, `_parse_lens_set_args`) to reduce closure/branch density while preserving command behavior
