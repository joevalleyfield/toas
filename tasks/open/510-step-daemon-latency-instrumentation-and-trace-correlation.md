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
