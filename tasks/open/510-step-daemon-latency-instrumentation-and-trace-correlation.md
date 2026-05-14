# 510 Step/Daemon Latency Instrumentation and Trace Correlation

## Objective
Add durable, low-overhead latency instrumentation for `toas step` across local CLI, RPC client, and daemon dispatch paths, with correlation that works both before and after async `run_id` assignment.

## Why
Observed `toas step` latency is materially higher than expected (~1.1s on repeated warm runs), and current visibility is insufficient to separate startup, transcript/history work, RPC transport, daemon dispatch, and model/tool execution costs.

## Scope
- keep instrumentation opt-in behind `TOAS_PERF_TRACE=1`
- emit phase timing for:
  - local step pipeline
  - RPC client request path
  - daemon default-op dispatch
- add durable `perf_trace` records in `events.jsonl`
- include correlation identifiers:
  - `trace_id` (always)
  - `run_id` (nullable when unavailable early)
- preserve existing stdout/history contracts unless trace mode is enabled

## Done When
- trace mode produces structured timing with phase breakdown across local and daemon flows
- pre-`run_id` and post-`run_id` timing can be correlated by shared `trace_id`
- durable `perf_trace` events are queryable via `toas history` and/or `rg`
- targeted tests and full suite pass

## Related
- `226` latency and behavior validation
- `370` step/daemon/llm reliability arc
- `489` daemon self-shell elimination via operator API
- `499` cli session step-local dependency-surface split
- `503` daemon run-store watch async-step phase split

## Progress
- added reusable perf recorder module:
  - `src/toas/perf.py`
- added opt-in phase timing emission (`[toas-perf]` JSON on stderr) for local step:
  - `read_log`
  - `prepare_session_transcript`
  - `resolve_runtime_generation_context`
  - `step`
  - `persist_step_outputs`
- added RPC client timing for:
  - `resolve_endpoint`
  - `build_request`
  - `transport_roundtrip`
- added daemon default-op timing for:
  - `request_workdir`
  - `run_op_capture_stdout`
- validated with targeted tests:
  - `tests/test_cli.py::test_run_step_local_appends_stdin_and_control_to_transcript`
  - `tests/test_daemon.py::test_handle_request_step_returns_stdout_and_applies_step`
  - `tests/test_daemon_local_ops.py::test_handle_default_op_logs_stdout_len`
- next slice:
  - persist durable `perf_trace` records with `trace_id` + nullable `run_id`
- landed durable `perf_trace` persistence in step-local path:
  - each `toas step` with `TOAS_PERF_TRACE=1` now appends `kind=perf_trace` record to `events.jsonl`
  - payload now includes `trace_id` (always), `run_id` (nullable), `trace_kind`, `total_ms`, `phases`, `op`, `rpc_mode`, and `ts_ms`
- landed first import-thinning slice for plain CLI path:
  - removed eager `toas.daemon` import from `toas.cli`; daemon module is now imported only inside `run_daemon`
  - removed eager `toas.llm` symbol imports from `toas.cli` fast path and shifted remaining runtime usage to lazy import/wrapper edges
  - retained compatibility surface for tests/daemon monkeypatch seam via lazy `cli.generate_assistant_message` wrapper
- measurement after slice:
  - `TOAS_PERF_TRACE=1 toas step` observed `cli.main.pre_main_imports` improved from ~973ms to ~917ms on measured run
  - end-to-end `Measure-Command { toas step }` remained ~1.18s on measured run, indicating additional startup/import contributors remain
- landed focused llm/openai startup de-poisoning slices (only this edge family):
  - removed `backend_policy -> llm` import edge by localizing `NO_THINKING` constant in `backend_policy`
  - removed eager `cli -> step -> llm` edge by replacing top-level step imports in `cli` with lazy wrappers
  - removed eager `cli_streaming -> llm` runtime type edge (PromptProgress type-only fallback)
  - removed eager `cli_streaming -> runtime.stream_presentation_edges -> llm` type edge (PromptProgress type-only fallback)
- import-time evidence after de-poisoning:
  - `-X importtime -m toas.cli step` no longer shows `openai`/`toas.llm` in startup import set
  - `cli.main.pre_main_imports` dropped to ~217ms on measured run (from ~900-2000ms range during poisoned-startup runs)
- current remaining cost profile:
  - `toas step` still incurs heavy llm/openai import cost during `resolve_runtime_generation_context` when a generation path is executed in-process
  - this is now in dispatch/runtime phase, not CLI startup import phase
- landed step-module import-thinning slice (focused on greedy `step.py` top-level imports):
  - moved branch-specific dependencies in `step.py` behind lazy helpers (`prompts`, `tools`, `tools_guidance`, `runtime.context_assembly`)
  - retained runtime compatibility surface by re-exporting `load_prompt_ref` via lazy wrapper
  - added granular perf markers for `step_module_import` and `step_inner_call`
- measurement after step import-thinning:
  - before: `step_module_import` ~1599ms, `step_inner_call` ~38ms, end-to-end empty `toas step` ~2.3s
  - after: `step_module_import` ~23ms, `step_inner_call` ~51ms, traced empty `toas step` ~0.58s (`ElapsedSeconds=0.583`)
  - startup remains ~270ms class (`cli.main.pre_main_imports`), now dominant alongside shell/process overhead
