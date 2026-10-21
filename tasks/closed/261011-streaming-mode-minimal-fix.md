Filed as: 261011-streaming-mode-minimal-fix
FKA:
AKA: TOAS_STREAM_STDOUT leak fix; stop streaming env var leaking into tool subprocesses
Legacy index:

keywords: runtime, tooling, implementation, historical, correctness, stream, transport, shell, boundaries

Parent: `261011-streaming-mode-env-leak-parent`

# Streaming Mode: Minimal Fix for Env Var Leak

Status: DONE; implemented and verified (2026-10-15)

## Completion

- Added `active_stream_stdout` / `current_stream_stdout` ContextVar in
  `src/toas/runtime/environment_policy.py` — an in-process-only transport
  signal that never enters the child process environment.
- `execute_plan_calls` accepts `stream_stdout_enabled` and wraps dispatch in
  `active_stream_stdout(...)`; `execute_plan` in `tools.py` forwards it.
- `run_subprocess` now chooses the streaming vs. capturing branch from
  `current_stream_stdout()` / `stream_stdout_override`, **not** from
  `effective_env["TOAS_STREAM_STDOUT"]`.
- `_spawn_streaming_process` no longer merges `os.environ.copy()`; the
  explicit `env` dict is authoritative, so intentionally-removed variables
  are not re-introduced.
- `step.py` no longer injects `TOAS_STREAM_STDOUT` into `effective_env`
  (both `_execute_plan` and `_execute_user_shell`); the flag is threaded
  explicitly to `execute_plan`.
- Updated tests that drove the streaming branch via the env var to use
  `stream_stdout_override=True` instead; dropped the assertion that
  `TOAS_STREAM_STDOUT` reaches the child env.

Verification:
- `uv run pytest` — 3511 passed, 100.00% coverage.
- The two originally-failing tests pass with `TOAS_STREAM_STDOUT=1` in the
  ambient environment:
    `test_execute_plan_calls_applies_process_environment_to_runtime_subprocess`
    `test_interpreter_script_preserves_nonzero_stderr`

## Objective

Stop `TOAS_STREAM_STDOUT` from leaking into the subprocess environment
of tool calls. Replace the env-var-based capture-strategy signal with an
explicit parameter or ContextVar so that only the shell tool (where
streaming is intended) uses the streaming subprocess path.

## Scope

Minimal, surgical changes. No transport schema changes. No stderr
separation in the streaming path. No daemon protocol changes.

## Changes

1. **`step.py`:** Stop injecting `TOAS_STREAM_STDOUT` into
   `effective_env`. Instead, pass the streaming mode as an explicit
   boolean (e.g. `stream_stdout_enabled`) through
   `execute_plan` → `execute_plan_calls` → `adapt_call_for_execution`
   → tool dispatch → `run_subprocess`.

   The `TOAS_STREAM_STDOUT` env var remains in the worker's own
   `os.environ` for the worker-level transport decisions
   (`async_step_runtime_worker.py`, `step_generation_runtime.py`), but
   is not propagated into the subprocess environment of tool calls.

2. **`execution.py`:** Accept and forward the streaming mode flag.
   Do not include `TOAS_STREAM_STDOUT` in
   `active_environment_overrides` / `default_process_env`.

3. **`shell_ops.py` `run_subprocess`:** Change the streaming/capturing
   decision to use an explicit `stream_mode` parameter (or
   `stream_stdout_override`) instead of reading
   `TOAS_STREAM_STDOUT` from `effective_env`. Default to `"capture"`.

   The shell tool's top-level caller (the daemon/step layer) passes
   `stream_mode="stream"` when in streaming mode. All other callers
   (interpreter, execution-plan, tests) use the default `"capture"`.

4. **`shell_streaming.py` `_spawn_streaming_process`:** Remove
   `os.environ.copy()` as the baseline. Use only the explicit `env`
   dict. The `env` parameter is already a complete environment by the
   time it reaches this function.

5. **`interpreter_ops.py`:** No change needed if `run_subprocess`
   defaults to `"capture"`. The interpreter will always use the
   capturing path, preserving stderr separation.

## Out of Scope

- Extending `tool_progress` event schema with stream tags
- Two-pipe streaming with stderr separation
- Daemon protocol changes
- Removing `TOAS_STREAM_STDOUT` from the worker-level transport
  (it stays for `async_step_runtime_worker` and
  `step_generation_runtime`)
- Changing the `active_environment_overrides` mechanism itself

## Acceptance

- `uv run pytest` passes with 100% coverage, including:
  - `tests/test_tools_execution.py::test_execute_plan_calls_applies_process_
    environment_to_runtime_subprocess`
  - `tests/test_tools_interpreter_ops.py::test_interpreter_script_preserves_
    nonzero_stderr`
- Both tests pass when run inside a TOAS session with
  `TOAS_STREAM_STDOUT=1` in the environment.
- The shell tool in streaming mode still streams subprocess stdout
  live to the operator (no regression in streaming behavior).
- No `TOAS_STREAM_STDOUT` in the subprocess environment of tool
  calls that use the capturing path.

## Files

- `src/toas/step.py`
- `src/toas/tools_cluster/execution.py`
- `src/toas/tools_cluster/shell_ops.py`
- `src/toas/tools_cluster/shell_streaming.py`
- `tests/test_tools_execution.py` (verify, not modify)
- `tests/test_tools_interpreter_ops.py` (verify, not modify)
- `tests/test_cli.py` (may need adjustment if tests set
  `TOAS_STREAM_STDOUT` env var)
- `tests/test_cli_session_commands.py` (same)
- `tests/test_daemon_async_runner.py` (same)
- `tests/test_runtime_policy.py` (same)

## Hygiene disposition — 2026-10-20

Status: CLOSED

Implementation and verification were already recorded on 2026-10-15. The current macOS full check also passes (3,585 tests, 100% coverage; 17 acceptance tests, Ruff and mypy). The parent retains the separate stderr-streaming design question.

Earlier current-reality descriptions above are historical evidence, not the
current implementation contract.
