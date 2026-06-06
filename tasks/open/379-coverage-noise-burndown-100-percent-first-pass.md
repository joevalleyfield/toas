## Goal
keywords: runtime, decomp, active, maintainability, coverage, burndown, reporting, missing-lines

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

## Next Targets

- identify next near-complete candidates for elimination from missing-lines output
- `386` landed; continue from simplified parser flow and prefer behavior-meaningful coverage over synthetic branch forcing
