## Goal
keywords: runtime, decomp, closed, maintainability, coverage, burndown, reporting, missing-lines

Reduce future coverage-report noise by driving selected small/medium modules to `100%` so they disappear from the missing-lines output.

## Why Now

After the first ratchet checkpoint (`375`), the next leverage move is shrinking noisy report surface so future gaps are concentrated in genuinely hard modules.

## Scope

- prioritize modules already near-complete coverage (`95%+`) for quick elimination
- land narrow deterministic tests to close remaining uncovered lines
- keep task slicing explicit per module so progress remains auditable
- record and apply a preference for explicit callable/functor classes over closure-heavy local state where refactors are needed for testability

## Intended Behavior

- coverage report contains fewer near-complete modules
- remaining report entries are higher-signal targets for deeper reliability work

## Constraints

- no semantic drift in runtime behavior
- no broad rewrites in this pass; keep changes incremental and test-first

## Done When

- first set of `95%+` targets are either at `100%` or split into justified follow-ons
- roadmap and subtasks reflect completed/remaining burn-down targets

## Progress

- completed first target set:
  - `380` (`rpc_transport.py`) to `100%`
  - `381` (`transcript.py`) to `100%`
- completed second target set:
  - `382` (`rpc_client.py`) to `100%`
  - `383` (`capability_prompts.py`) to `100%`
- partial third target set:
  - `384` (`shell_grants.py`) to `100%`
  - `385` (`shell_intent.py`) closed at `99%` by design-signal decision
- fourth target set:
  - `387` (`secrets.py`) to `100%`
  - `388` (`rpc_windows.py`) to `100%`
- fifth target set:
  - `389` (`rpc_protocol.py`) to `100%`
- sixth target set:
  - `390` (`shell_intent.py`) to `100%`
  - `391` (`rpc_unix.py`) to `100%`
  - `392` (`rpc_tcp.py`) to `100%`
- these modules now disappear from coverage missing-lines report (`skip_covered = true`)
  - full suite now reports `12 files skipped due to complete coverage`
- seventh target set (post-refactor quick wins from newly extracted modules):
  - `runtime/step_generation_runtime.py` to `100%` (TypeError fallback + re-raise)
  - `runtime/operator_command_prompt_workspace.py` to `100%` (`/graph` unknown token)
  - `runtime/frontier_resolution.py` to `100%` (near-miss YAML hint)
  - `cli_host_commands.py` to `100%` (`--session` missing arg)
  - `cli_async_commands.py` to `100%` (`_watch_event_text` early returns)
  - `daemon/__init__.py` to `100%` (thin wrapper delegations)
  - `graph_control_state_edges.py` to `100%` (guard conditions)
  - `cli_dispatch.py` to `100%` (option parse errors + surface reason path)
  - `runtime/stream_subscribe_runtime.py` to `100%` (event seq guards)
  - `runtime/policy_edges.py` to `100%` (env truthy/falsy)
  - full suite: `1811 passed`, `87 files skipped due to complete coverage`
  - files below 100%: `37 → 27` (10 eliminated)
- eighth target set (smaller batch, 3 files):
  - `runtime/stream_pacing_summary.py` to `100%` (empty-line skip, bad JSON, non-dict)
  - `tools_cluster/event_graph.py` to `100%` (get_root, temporal_order fallback)
  - `tools_cluster/shell_ops.py` at `95%` — 10 lines in error paths (except/pass, dead _probe_process_snapshot, deep exception handler). Not worth forcing.
  - files below 100%: `27 → 25` (2 eliminated)
- ninth target set:
  - `runtime/cancel_latency_summary.py` to `100%` (empty percentile, empty lines, non-dict, empty data)
  - files below 100%: `25 → 24` (1 eliminated)
- tenth target set:
  - `graph_record_writers.py` to `100%` (surface_rebind, surface_guardrail, surface_bind reason, surface_select)
  - `operator_api.py` to `100%` (rebind_surface, index_rebuild_message, _prov_summary unknown, _ensure_session_path_compat no-legacy + success)
  - files below 100%: `24 → 22` (2 eliminated)
- eleventh target set:
  - `cli_dispatch_ops.py` to `100%` (missing values, bad arg counts, unknown options for step, step-async, surface, graph)
  - `runtime/operator_command_config_help.py` to `98%` (3 dead/untestable lines: fallback import, dead elif, dead yaml_position compat)
  - files below 100%: `22 → 21` (1 eliminated)
- twelfth target set:
  - `tools_cluster/file_ops.py` to `100%` (validation errors for replace_range and replace_block, _normalize_indent, _apply_indent)
  - files below 100%: `21 → 20` (1 eliminated)
- thirteenth target set:
  - `tools_cluster/apply_patch_ops.py` to `98%` (validation errors, move success, helpers edge cases)
  - files below 100%: `20 → 20` (0 eliminated, 3 lines are dead code or untestable)
- fourteenth target set:
  - `tools.py` to `100%` (procedure validation, _normalize_indent, _apply_indent, _build_env_with_overrides, _resolve_workspace_roots)
  - files below 100%: `20 → 19` (1 eliminated)
- fifteenth target set:
  - `runtime/context_assembly.py` to `98%` (lens artifact no source_pointers, _first_non_empty_line, _extract_goal_cue, _normalize_source_pointers, lens event actions, validate_context_packet coverage failure)
  - files below 100%: `19 → 19` (0 eliminated, 5 lines are deep validation paths)
- sixteenth target set (finish the three 98% modules):
  - `runtime/context_assembly.py` to `100%` (non-string content goal cue, no-source-pointers evidence refs, conflict from message artifacts, non-string evidence snippets)
  - `runtime/operator_command_config_help.py` to `100%` (removed dead `_result_node` fallback import and dead `elif` branch; added yaml_position choices test)
  - `tools_cluster/apply_patch_ops.py` to `100%` (removed dead `*** End of File` parser branch; added invalid-hunk-kind test)
  - files below 100%: `19 → 16` (3 eliminated)
  - also fixed shell test cwd flake under xdist (replace `Path.cwd()` assertions with observed cwd)
  - also added `.toas/` to `.gitignore`

## First Pass Complete

Files below 100%: `37 → 21` (16 eliminated). Remaining 21 files are mostly:
- Dead code (3 lines in operator_command_config_help.py)
- Error handlers (shell_ops.py, step_runtime.py)
- LLM testing (llm_harness.py)
- Windows-specific code (shell_streaming.py)
- Validation errors (file_ops.py, apply_patch_ops.py, tools.py, context_assembly.py)
- Async error paths (async_activity_store_impl.py)

These are much harder to test than the initial quick wins. Consider the first pass complete.

## Current State (after sixteenth target set)

Files below 100%: `19 → 16` (3 eliminated: context_assembly, operator_command_config_help, apply_patch_ops).
Remaining 16 files:

- 96%: `step_runtime.py` (12 lines) — error paths in async runtime
- 95%: `shell_ops.py` (10 lines) — deep exception handler + dead `_probe_process_snapshot`
- 94%: `async_activity_store_impl.py` (26 lines) — error paths in activity store
- 91%: `operator_command_extract_replay.py` (29 lines) — validation errors
- 90%: `shell_streaming.py` (14 lines), `step.py` (56 lines), `graph.py` (56 lines)
- 89%: `llm_harness.py` (15 lines), `prompts.py` (29 lines)
- 88%: `async_step_runtime_worker.py` (41 lines)
- 83%: `llm.py` (102 lines), `session_host_process.py` (45 lines)
- 77%: `cli.py` (123 lines)
- 38%: `cli_session_commands.py` (118 lines)
- 37%: `experiments/async_stdio_todo_ipc.py` (71 lines)
- 33%: `cli_demo_async_client.py` (249 lines)

Coverage: 92.39% (gate: 95%), 16 files below 100% (gate: 13).

## Path Forward

To hit the 13-file cap, need to eliminate 3 more modules. Best candidates:

1. **shell_ops.py** (95%, 10 lines) — `_probe_process_snapshot` is dead code (remove); remaining lines are deep exception handler (test if worth it)
2. **step_runtime.py** (96%, 12 lines) — error paths in async runtime (may need mocking)
3. **async_activity_store_impl.py** (94%, 26 lines) — error paths (may need mocking)
4. **llm_harness.py** (89%, 15 lines) — streaming error paths
5. **shell_streaming.py** (90%, 14 lines) — Windows-specific code

Alternatively, adjust coverage gates to match reality.

## Next Targets

- identify next near-complete candidates for elimination from missing-lines output
- `386` landed; continue from simplified parser flow and prefer behavior-meaningful coverage over synthetic branch forcing

## Follow-up Progress

- eliminated additional long-standing near-complete noise while evaluating the `push-xtwlxqpzkvmt` merge:
  - `tools_cluster/shell_ops.py` to `100%` via diagnostic write-failure, process snapshot success/failure, and assistant subprocess exception tests
  - `tools_cluster/shell_streaming.py` to `100%` via Windows stdout-reader final-flush coverage
  - `tools_cluster/rendering.py` to `100%` via shell stdout import-block and fence-language edge cases
  - `tasks.py` to `100%` via task-adapter abstract fallthroughs and bad task-id match handling
- files below 100% reduced to the coverage gate cap (`14 -> 13`) without changing production behavior
- completed additional target sets to drive near-complete modules to 100%:
  - `runtime/step_runtime.py` to `100%` (removed unreachable frontier tail invariant guard; added YAML near-miss syntax error & empty consequence runtime error checks)
  - `runtime/async_activity_store_impl.py` to `100%` (removed dead unused `_capture_watch_snapshot` helper; added invalid poll interval float & exception lane-phase defaults branch coverage)
  - `cli_demo_async_client.py` to `100%` (added mock tests covering select timeouts, subprocess exit, stderr read failures, and reader loop exceptions; covered SystemExit line via runpy test runner)
  - `runtime/operator_command_extract_replay.py` to `100%` (added tests covering missing validation, queue status handling, and shlex split error branches)
  - `runtime/async_step_runtime_worker.py` to `100%` (added comprehensive edge-case tests covering tool buffer flushes, process exceptions, stdout proxies, and callback triggers)
  - `prompts.py` to `100%` (added tests covering invalid prompt reference handling, yaml parse failures, target resolution legacy path, and dynamic/template compositions)
- files below 100% reduced from `10` to `7` (3 eliminated), overall coverage elevated to `97.04%` with `109` files completely covered and skipped
- driven `src/toas/cli_session_commands.py` to `100%` coverage by resolving mock event prefix matching and stdin mode capturing for debug prompt progress testing; files below 100% reduced from `7` to `6`, and overall coverage reached `97.23%` with `110` files completely covered and skipped.

## Closeout

Closed 2026-06-14. The first-pass burndown goal was met: near-complete module
noise was substantially reduced, coverage gates were raised, and later
follow-up work drove several formerly noisy modules to `100%`.

Architecture-era work then introduced new low-coverage boundary modules, but
those are decomposition and ownership signals rather than unfinished `379`
scope. Route new cleanup through `400` when it requires module-boundary work,
and through `374` when focused tests are the needed evidence.

