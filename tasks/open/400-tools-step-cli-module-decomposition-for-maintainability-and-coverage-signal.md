## Goal
keywords: runtime, decomp, active, maintainability, decomposition, coverage, cli, tools, step

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
- treat retired warm-lane surfaces and stale compatibility shims as removal candidates, not decomposition targets

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
  - `src/toas/daemon/async_runner.py` (single canonical async execution lane)
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
- remove retired warm/self-shell scaffolding that is no longer behaviorally reachable
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
- post-runtime-architecture slices name their owning domain before adding more
  broad `runtime/`, `cli`, or adapter modules

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
- `491`: daemon async-runner post-warm retirement pass (`async_runner_warm.py` removal + caller/test cleanup)
- `492`: operator API seam consolidation for CLI local session/history wrappers (reduce residual importlib/compat coupling)
- `493`: tools compatibility shim retirement (`tools_execution.py`, `tools_registry.py`, `tools_rendering.py` wrappers) after caller migration
- `494`: daemon compatibility wrapper retirement (`daemon_*` shim modules) after import-path migration
- `495`: runtime step/command boundary split second pass (`step_runtime` and `operator_command_extract_replay` high-branch helpers)
- `496`: CLI façade thinning (`cli.py`) by extracting remaining non-dispatch command clusters to focused modules
- `497`: shell-ops subprocess boundary split and stream-policy normalization (`tools_cluster/shell_ops.run_subprocess` hotspot)
- `498`: step-runtime frontier consequence split second pass (`runtime/step_runtime._execute_frontier_consequences` hotspot)
- `499`: CLI session step-local dependency-surface split (`cli_session_commands.run_step_local` hotspot)
- `500`: runtime prompt/workspace intent+lens decomposition second pass (`operator_command_prompt_workspace._handle_intent`/`_handle_lens` hotspots)
- `501`: shell streaming run-subprocess phase split and coverage hardening (`tools_cluster/shell_streaming.run_streaming_subprocess` hotspot)
- `502`: replay runtime queue-until-boundary second pass (`operator_command_extract_replay._run_queue_until_boundary` hotspot)
- `503`: daemon run-store watch-async-step phase split (`daemon/run_store.watch_async_step` hotspot)
- `506`: graph message/event store phase split (`graph.py` durable append/query/lineage hotspot reduction)
- `507`: step-runtime orchestration decomposition third pass (`runtime/step_runtime.py` consequence assembly + projection seams)
- `508`: daemon facade reduction third pass (`daemon/__init__.py` transport/bootstrap wrapper thinning)
- `260614-daemon-free-host-local-command-surface`: 470 follow-on seam to give stdio host request handling a narrow daemon-free local command surface instead of depending on the broad `toas.cli` facade.

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
- post-`436` reassessment opened the next decomposition queue focused on remaining high branch-density hotspots: `config` parsing/overrides split, `cli_dispatch` command-routing split, daemon async runner split, `tools_cluster.file_ops` matcher/diagnostic split, runtime config-backend shaping split, and a final `step_runtime.run_step` phase split
- config parsing/overrides split landed: `config.py` now delegates parsing/coercion to `config_parsing.py` and nested merge/materialization to `config_overrides.py` with compatibility wrappers retained and full-suite parity validation (`992 passed`)
- CLI dispatch routing split landed: `cli_dispatch.py` now delegates argument parsing branches for `watch`/`prompt`/`ancestry` to `cli_dispatch_ops.py`, reducing branch density in `dispatch_main` while retaining exact command behavior (`995 passed`)
- daemon async-runner split landed: in-process execution lifecycle moved out of nested closure into `daemon/async_runner_warm.py`, leaving `daemon/async_runner.py` as async orchestration and improving direct seam testability (`997 passed`)
- tools file matcher/diagnostic split landed: `tools_cluster/file_ops.py` now delegates block-pattern selection and mismatch diagnostics to `tools_cluster/file_match_ops.py`, reducing replace operation branch density and isolating matcher-specific tests (`999 passed`)
- runtime config/backend shaping split landed: backend list/add/set/remove/capture logic extracted from `runtime/operator_command_config_help.py` to `runtime/operator_config_backend_ops.py`, making config/help command routing thinner and easier to target in tests (`1001 passed`)
- step runtime phase split landed: `runtime/step_runtime.run_step` now delegates transcript-delta assembly and frontier consequence execution to focused helpers (`_build_new_transcript_nodes`, `_execute_frontier_consequences`) with direct helper coverage and parity (`1003 passed`)
- CLI replay-script flow split landed: `cli.py` now delegates progressive replay execution to `cli_replay_script.run_replay_script_local` via explicit dependency bundle, reducing command-handler density in `cli.py` while preserving CLI surface behavior
- post-455 `code_survey` checkpoint rerun (top functions) highlighted `operator_config_backend_ops.config_backend_result`, `config_parsing.parse_config_value`, and `session_step_edges.apply_result_side_effects` as compact high-leverage decomposition seams under the 400/374 overlap
- latest decomposition pass split `/config backend` handling into focused helper branches in `runtime/operator_config_backend_ops.py` (`list|add|remove|set|capture`), keeping facade dispatch thin and validation paths isolated
- latest decomposition pass split config parsing coercion helpers in `config_parsing.py` (`_parse_choice`, `_parse_int_nonnegative`, `_parse_float_nonnegative`, `_parse_bool`, `_field_default_for_key`) to reduce branch density in `parse_config_value`
- latest decomposition pass split session result side-effects fan-out in `runtime/session_step_edges.py` into focused helpers (`_apply_queue_updates`, `_apply_lens_updates`, `_apply_context_updates`, `_apply_workspace_updates`, `_apply_secret_updates`, `_apply_config_updates`, `_apply_config_saves`, `_apply_session_updates`)
- latest decomposition pass split `runtime/operator_command_prompt_workspace._handle_lens` nested closures into module-level helpers (`_extract_lens_fenced_distillation`, `_parse_lens_source_ids`, `_collect_known_message_ids`, `_parse_lens_set_args`) to reduce closure/branch density while preserving command behavior
- latest tools cleanup pass removed legacy duplicate replace-block matcher/diagnostic helpers from `tools.py` (now solely owned by `tools_cluster/file_match_ops.py`), shrinking `tools.py` and reducing stale wrapper surface
- post-`489` reorientation: warm lane retired and daemon async path now runs through canonical operator API seam; next decomposition focus shifts from warm-lane extraction to warm-lane retirement and compatibility-shim reduction.
- `491` completed and moved to `tasks/closed/` after removing retired `daemon/async_runner_warm.py` artifact; no live imports remained and daemon async/full-suite parity was revalidated (`1354 passed`).
- `496a` landed: extracted streaming presentation classes from `cli.py` into `cli_streaming.py` with compatibility aliases (`cli._StreamPresenter`, `cli._ClosedSetMarkerStreamEscaper`) retained for stable callers/tests (`163 passed` targeted slice validation).
- `496b` landed: extracted session-view command cluster from `cli.py` into `cli_session_views.py` (`intents/history/transcript/rebuild/session-path/llm-input/prompt(s)` locals) with thin wrapper delegation retained in `cli.py` and targeted CLI parity validation (`176 passed`).
- `496c` landed: extracted daemon/runtime command wrapper logic from `cli.py` into `cli_runtime_commands.py` (`run_daemon` action handling and shutdown hygiene) with thin delegation retained and targeted CLI/daemon parity validation (`258 passed`).
- `496d` landed: extracted analysis command locals from `cli.py` into `cli_analysis_commands.py` (`diff`/`ancestry`/`index rebuild` local handlers) with wrapper delegation retained and targeted CLI/history parity validation (`257 passed`).
- post-`496` AST survey checkpoint:
  - `cli.py` reduced from 1198 to 1004 lines after `496a`-`496d`.
  - highest remaining decomposition pressure shifted to runtime orchestration/replay (`step_runtime`, `operator_command_extract_replay`) and session-generation seam (`cli_session_commands`), followed by shell execution complexity (`tools_cluster/shell_ops`).
  - reordered near-term execution priority: `495` -> `492` -> `493` -> `494`.
- `495` first extraction slice landed:
  - replay queue/state helpers moved from `runtime/operator_command_extract_replay.py` into new focused module `runtime/replay_queue_edges.py`.
  - `operator_command_extract_replay.py` now imports queue-state helpers via thin compatibility aliases, reducing local orchestration density without behavior changes.
- post-`495` AST survey checkpoint:
  - `runtime/operator_command_extract_replay.py` reduced from 578 to 499 lines.
  - remaining top function hotspots are unchanged in ordering (`shell_ops.run_subprocess`, `step_runtime._execute_frontier_consequences`, `cli_session_commands.run_step_local`), confirming next sequence still: `492` -> `493` -> `494`.
- `492` seam consolidation slice landed:
  - `operator_api.py` no longer imports CLI internals for heads/rebuild helpers.
  - moved lineage/provenance summarization and session-path/newline compatibility logic into `operator_api.py` with direct config/graph/runtime-edge usage.
  - retained operator API behavior parity for `step_once`, `heads_lines`, `history_lines`, and `rebuild_session` (`164 passed` targeted operator/CLI/acceptance validation).
- `493` shim retirement slice landed:
  - removed compatibility shim modules `tools_execution.py`, `tools_registry.py`, and `tools_rendering.py`.
  - migrated callers/tests to direct `tools_cluster.execution|registry|rendering` imports.
  - retained tools/runtime behavior parity under targeted validation (`335 passed`).
- `494` daemon shim retirement slice landed:
  - removed compatibility shim modules `daemon_async_runner.py`, `daemon_backend_lifecycle.py`, `daemon_handlers.py`, `daemon_local_ops.py`, `daemon_op_dispatch.py`, `daemon_process_control.py`, `daemon_request_contract.py`, and `daemon_run_store.py`.
  - migrated callers/tests to direct `toas.daemon.*` imports.
  - retained daemon behavior parity under targeted validation (`191 passed`).
- `500` completed and moved to `tasks/closed/` after decomposing runtime prompt/workspace intent+lens hotspots into focused helper seams (`_handle_intent`/`_handle_lens` slim-down, including lens remove/reset extraction) with targeted parity validation.
- `501` completed and moved to `tasks/closed/` after phase-splitting `tools_cluster/shell_streaming.run_streaming_subprocess` into explicit process/reader/wait/drain/final-assembly seams plus reader lifecycle/event-loop helpers, with targeted parity + full-suite validation.

## Reoriented Next Slices (Post-489)

Current hotspots with high leverage:
- `src/toas/cli.py` still carries broad façade/IO behavior and dense branches.
- `src/toas/runtime/operator_command_extract_replay.py` remains one of the largest branchy runtime handlers.
- `src/toas/tools_cluster/shell_ops.py` still carries dual-path complexity (streaming policy + timeout/flush paths).
- `src/toas/daemon/async_runner_warm.py` remains as a retired-lane artifact and should be removed to reduce conceptual load.

Execution order:
1. `500` runtime prompt/workspace intent+lens decomposition second pass.
2. `501` shell streaming phase split + direct coverage hardening.
3. `502` replay queue-until-boundary second pass.
4. `503` daemon run-store watch-async-step phase split.
5. rerun AST/code-survey ranking and continue bounded hotspot slices.

- post-`492`/`493`/`494` stabilization survey confirms next decomposition focus should shift to remaining top hotspots:
  - `497` for `tools_cluster/shell_ops.run_subprocess`
  - `498` for `runtime/step_runtime._execute_frontier_consequences`
  - `499` for `cli_session_commands.run_step_local`

- post-498/499 rerank opened next hotspot queue: `500`-`503` focused on runtime prompt/workspace handlers, shell streaming phase splits, replay boundary orchestration, and daemon watch run-store phase decomposition.
- `502` completed and moved to `tasks/closed/` after splitting replay queue-until-boundary orchestration into focused helpers (plan-state validation, skip/cancel transitions, outcome classification, boundary render) with targeted/full-suite parity validation.
- `503` completed and moved to `tasks/closed/` after phase-splitting daemon watch async-step flow into request-parse/baseline/follow/snapshot/response helpers with focused helper tests and full-suite parity validation.
- follow-up hardening (2026-05-25): added `daemon/run_store` debug-log reentrancy guard (`_debug_log_safe`) to prevent recursive debug-hook watch/event deadlock in poll snapshot paths; validated with focused `tests/test_daemon_run_store.py` watch/follow/cancel confidence slice.
- post-`503` survey opened next decomposition queue: `506`-`508` focused on `graph.py` durable history seams, `runtime/step_runtime.py` orchestration follow-through, and `daemon/__init__.py` facade thinning.
- `508` completed and moved to `tasks/closed/` after extracting daemon facade wrapper clusters into focused modules (`facade_async_ops`, `facade_dispatch_ops`, `facade_backend_state_ops`, `facade_local_ops`) and consolidating dispatch-runtime assembly through a unified seam with targeted/full-suite parity validation.
- `260614-daemon-free-host-local-command-surface` completed and moved to `tasks/closed/`: added `cli_local_commands.py` as the narrow daemon-free local command dependency surface for host request handling, replacing the previous `toas.cli` dependency in `cli_host_commands`.

## Post-Architecture Recenter (2026-06-14)

The architecture masterplan and backend-lifecycle work changed the shape of the
decomposition problem. `400` remains the implementation owner for module
boundary cleanup, but future slices should be motivated by domain ownership
rather than by moving code into `runtime/` by default.

Fresh planning signals after the backend-lifecycle/logging/architecture work:

- coverage report: total coverage remains high (`97%`), but the largest noisy
  surfaces are newly important boundary modules: `cli_local_commands.py`
  (`34%`) and `runtime/request_handler_assembly.py` (`54%`), followed by
  `session_host_process.py` (`87%`) and the legacy `cli.py` facade (`77%`).
- code survey: the largest function hotspots include
  `session_host_process._stream_stream_subscribe_request`,
  `async_step_runtime_worker.start_async_step`, `step_runtime.run_step`, and
  `request_handler_assembly.build_local_request_handler_runtime`.
- architecture guidance: use `docs/runtime-ownership.md` to name the owning
  domain first. Adapter assembly, activity lifecycle, session host supervision,
  model backend lifecycle, transport/protocol, and surface rendering should not
  blur together merely because they currently live near each other.

Next decomposition queue from `400`'s point of view:

1. Split or clarify `cli_local_commands.py` around local surface-adapter
   commands versus runtime-domain calls, adding tests that lock the adapter
   contract instead of treating low coverage as a standalone goal.
2. Split `runtime/request_handler_assembly.py` into request-handler assembly
   policy and concrete local handler wiring if that boundary can be named
   cleanly from the domain map.
3. Revisit `session_host_process._stream_stream_subscribe_request` as Session
   Host Supervision carrying Activity Lifecycle stream semantics; keep final
   terminality ownership outside the host.
4. Continue `cli.py` facade thinning only when a remaining cluster has a clear
   owning module and compatibility surface.

`374` should supply testability and smell evidence for these slices. `379` has
served its first-pass coverage-noise role and should not remain open as the
active owner for new architecture-era coverage gaps.

Progress:

- 2026-06-14: First post-architecture local command slice landed. Extracted
  default-op host surface commands from `cli_local_commands.py` into
  `cli_local_surface_commands.py`, keeping `cli_local_commands.py` as the
  compatibility/dependency surface for `run_step_local` and host request
  assembly. Added direct adapter-contract tests for heads/intents/transcript/
  llm-input/prompt/prompts so local surface behavior is locked without pulling
  in the broader step runtime compatibility module.
- 2026-06-14: Second post-architecture request-handler slice landed. Extracted
  local host/request wiring from `runtime/request_handler_assembly.py` into
  `runtime/local_request_handler_edges.py`, leaving request-handler assembly to
  compose dispatch runtimes while the new edge module owns local async step,
  subscribe-follow, default-op capture, cancel/watch, and backend lifecycle
  adapter wiring. Added direct edge tests for explicit backend unavailability,
  default-op capture, subscribe follow-mode, async dependency threading, and
  backend lifecycle delegation.
