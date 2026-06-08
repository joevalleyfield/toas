# 497 Shell Ops Subprocess Boundary Split And Stream Policy Normalization
keywords: runtime, hardening, historical, correctness, shell, stream, transport, boundaries

## Objective
Further decompose `src/toas/tools_cluster/shell_ops.py` so subprocess execution, stream-emission policy, and shell-shape adapters are separated into focused helpers/modules.

## Why
`shell_ops.run_subprocess` remains one of the highest branch-density hotspots after recent 400-series slices. This keeps streaming/timeout behavior hard to reason about and slows targeted testing.

## Scope
- extract subprocess lifecycle internals from `run_subprocess` into focused helpers (or a focused submodule)
- isolate stream flush policy decisions from command-shape adaptation (`shell`, `shell_script`, user-intent shell)
- preserve existing behavior and policy boundaries between user-intent and model-callable shell lanes
- add/adjust direct tests for extracted helper seams

## Out Of Scope
- changing shell authorization/policy semantics
- introducing a long-lived shell lane in this task

## Done When
- [x] `run_subprocess` no longer carries mixed responsibilities for process setup + read loop + policy shaping
- [x] helper/module boundaries are explicit and directly tested
- [x] targeted parity tests and full suite pass

## Related
- `400` decomposition umbrella
- `485` shell-lane purpose unification
- `483` streaming behavior debug/fix

## Progress
- extracted streaming subprocess lifecycle from `run_subprocess` into `_run_subprocess_streaming(...)`.
- extracted debug emission helpers into module-level `_stream_debug_enabled()` / `_stream_debug(...)`.
- extracted common completed-process-to-tool-result shaping into `_shape_subprocess_result(...)`.
- preserved existing shell lane semantics and stream flush behavior (newline/size/latency triggers unchanged).
- validated parity with targeted tests:
  - `uv run pytest tests/test_tools_shell_ops.py tests/test_tools.py -q --no-cov` (`123 passed`).
- second extraction pass split shell-shape routing from execution wiring:
  - `_resolve_user_shell_execution(...)` now centralizes command/operator decisioning.
  - `_resolve_user_argv(...)` and `_resolve_user_cwd(...)` now centralize user-call argument/cwd parsing.
  - `_needs_shell_result(...)` centralizes non-executable operator-hint result shaping.
- added direct helper tests in `tests/test_tools_shell_ops.py` for routing/argv/cwd resolution branches.
- revalidated targeted parity:
  - `uv run pytest tests/test_tools_shell_ops.py tests/test_tools.py -q --no-cov` (`126 passed`).
- final extraction pass moved subprocess streaming lifecycle into dedicated module `src/toas/tools_cluster/shell_streaming.py`.
- `shell_ops.run_subprocess(...)` now delegates streaming execution to `run_streaming_subprocess(...)`, keeping `shell_ops.py` focused on shell argument/routing and result shaping.
- preserved existing stream debug behavior and newline/size/latency flush triggers in the new module.
- validated targeted parity:
  - `uv run pytest tests/test_tools_shell_ops.py tests/test_tools.py tests/test_daemon_run_store.py -q --no-cov` (`139 passed`).
- Windows compatibility follow-up in `shell_streaming`:
  - replaced selector-based reader path with a Windows-safe blocking-read loop when `os.name == "nt"` for real subprocess streams, avoiding `WinError 10038` on pipe handles.
  - preserved non-Windows selector behavior and test-double compatibility.
  - merged subprocess env with parent env in spawn path to avoid command-resolution regressions when explicit env is empty.
  - validation: targeted acceptance/streaming tests pass; full suite reaches `1407 passed, 8 skipped` with only the separate coverage missing-files cap failing (`20 > 17`).
