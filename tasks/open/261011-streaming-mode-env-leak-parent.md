Filed as: 261011-streaming-mode-env-leak-parent
FKA:
AKA: TOAS_STREAM_STDOUT leak; streaming env var design; subprocess capture strategy; tool stream channel design
Legacy index:

keywords: runtime, tooling, investigation, inception, contract, stream, transport, shell, boundaries

# Streaming Mode: Env Var Leak and Capture Strategy Design

Status: INCEPTION; environment leak fixed; separate stderr streaming remains a design question

## Objective

The environment leak is fixed. Retain the design rationale and the prospective
question of preserving distinct stdout/stderr in streamed tool results. This
parent is reference material until a concrete operator need warrants that
extension; it does not own production implementation.

## Root Cause (Confirmed)

When a TOAS worker process runs with `TOAS_STREAM_STDOUT=1` in its
environment (set by the daemon/host to indicate "stream subprocess
stdout live to the operator"), that variable leaks into the subprocess
environment of every tool call that goes through `run_subprocess`.

The leak path:

1. Daemon sets `TOAS_STREAM_STDOUT=1` in the worker process env.
2. `step.py` `_execute_plan` injects it into `effective_env` →
   `default_process_env`.
3. `execution.py` `execute_plan_calls` wraps in
   `active_environment_overrides(default_process_env)`.
4. `shell_ops.py` `run_subprocess` merges `os.environ` + overrides into
   `inherited_env`, then reads
   `effective_env.get("TOAS_STREAM_STDOUT")` to decide streaming vs.
   capturing.
5. Any nested tool call (interpreter, execution-plan python_script, etc.)
   that calls `run_subprocess` without an explicit
   `stream_stdout_override` inherits the flag and switches to the
   streaming path.

Two distinct bugs result:

- **stderr loss:** `_spawn_streaming_process` sets
  `stderr=subprocess.STDOUT`, merging streams at the OS level.
  `_completed_process` returns `stderr=""` by construction. Any tool
  that routes through the streaming path silently loses stderr
  separation. Affects `interpreter_script` and any other tool that
  depends on distinct stdout/stderr.

- **env re-introduction:** `_spawn_streaming_process` does
  `os.environ.copy()` as its baseline, then updates with the explicit
  `env` dict. Variables that `run_subprocess` intentionally removed via
  overrides (value=None) are re-introduced from the `os.environ`
  baseline. Affects any tool call that removes env vars.

Both bugs are triggered by the ambient `TOAS_STREAM_STDOUT=1` in the
worker process env leaking into tool subprocess calls that should use
the capturing path.

## Design Questions

### Why is an environment variable the config channel?

The env var's only real advantage is cross-process visibility: the
daemon sets it in the worker's env, and the worker's `run_subprocess`
reads it without the daemon passing it through an RPC parameter. But
this crosses a process boundary where it shouldn't, and then leaks
across tool-call boundaries where it should.

The variable conflates two different concerns:
- **Process-level transport mode:** "this TOAS worker is in streaming
  mode and should pipe subprocess stdout live to the operator."
- **Per-call subprocess capture strategy:** "for this specific
  subprocess, should I use the streaming pipe or the capturing pipe?"

These should be orthogonal. The transport mode is set once at the worker
boundary. The capture strategy is a per-call decision that should be
made by an explicit parameter or context variable, not an ambient env
var.

### Alternative config channels

| Channel | Mechanism | Pros | Cons |
|---|---|---|---|
| Explicit parameter | `stream_mode: "stream" \| "capture"` on `run_subprocess` | Deterministic, testable, no ambient state | Caller must know the mode |
| ContextVar | `active_tool_stream_mode("stream")` context manager | No parameter threading; scoping explicit and testable | Less visible in call signatures |
| Env var (current) | `TOAS_STREAM_STDOUT=1` in subprocess env | Simple, cross-process | Leaks into nested calls; conflates transport with capture; hard to test |

### Does the transport require merging stderr into stdout?

No. The `tool_progress` event is `{"text": str}` on lane `"tool"` — a
single untagged text payload. This is a presentation choice, not a
transport constraint. The daemon RPC can carry arbitrary JSON. The
streaming path could use two pipes with tagged chunks
(`{"stream": "stdout"|"stderr", "text": str}`) and a multiplexed reader
thread. The current single-pipe merge is an implementation shortcut.

Long-term: extend the streaming path to preserve stderr separation with
tagged chunks. Near-term: document that streaming mode does not preserve
stderr separation, and ensure only the shell tool (where it's intended)
uses the streaming path.

## Proposed Direction

1. **Keep `TOAS_STREAM_STDOUT` as a worker-level transport flag.** The
   daemon sets it in the worker process env. The worker's top-level
   step handler reads it once and decides "I'm in streaming mode."

2. **Propagate the mode as an explicit parameter or ContextVar through
   the tool execution path.** When the worker is in streaming mode, it
   passes `stream_mode="stream"` into `execute_plan_calls` →
   `adapt_call_for_execution` → tool dispatch → `run_subprocess`. This
   is a process-internal signal, not an env var in the subprocess.

3. **Do not inject `TOAS_STREAM_STDOUT` into
   `default_process_env` / `active_environment_overrides`.** It stays
   in the worker's own `os.environ` for the transport layer, but is not
   propagated into the subprocess environment of tool calls.

4. **Fix `_spawn_streaming_process` to not re-merge `os.environ`.**
   Use only the explicit `env` dict passed to it. By the time
   `run_subprocess` calls the streaming path, `effective_env` is
   already a complete environment. The second `os.environ.copy()` is
   redundant and re-introduces removed variables.

5. **Extend the streaming path to preserve stderr separation** (long-
   term). Use two pipes with tagged chunks and a multiplexed reader.
   Extend the `tool_progress` event schema to carry a stream tag.

## Affected Files

- `src/toas/step.py` — injects `TOAS_STREAM_STDOUT` into
  `effective_env`
- `src/toas/tools_cluster/execution.py` — propagates
  `default_process_env` into `active_environment_overrides`
- `src/toas/tools_cluster/shell_ops.py` — reads
  `TOAS_STREAM_STDOUT` from `effective_env` to decide capture strategy
- `src/toas/tools_cluster/shell_streaming.py` — `stderr=subprocess.STDOUT`
  merge; `os.environ.copy()` baseline in `_spawn_streaming_process`
- `src/toas/tools_cluster/interpreter_ops.py` — calls
  `run_subprocess` without `stream_stdout_override`
- `src/toas/runtime/async_step_runtime_worker.py` — reads
  `TOAS_STREAM_STDOUT` for worker-level streaming decisions
- `src/toas/runtime/step_generation_runtime.py` — reads
  `TOAS_STREAM_STDOUT` via `_env_flag_enabled`
- `src/toas/runtime/policy.py` — `resolve_stdout_stream` reads
  `TOAS_STREAM_STDOUT` from env_modifiers

## Evidence

Two test failures when running inside a TOAS session with
`TOAS_STREAM_STDOUT=1` in the environment:

- `tests/test_tools_execution.py::test_execute_plan_calls_applies_process_
  environment_to_runtime_subprocess` — env var removal not effective
  because `_spawn_streaming_process` re-merges `os.environ`
- `tests/test_tools_interpreter_ops.py::test_interpreter_script_preserves_
  nonzero_stderr` — stderr empty because streaming path merges
  `stderr` into `stdout`

Both pass when `TOAS_STREAM_STDOUT` is not set in the environment.

## Children

- `261011-streaming-mode-minimal-fix` — stop leaking
  `TOAS_STREAM_STDOUT` into tool subprocess env; use explicit
  parameter/ContextVar for capture strategy

## Current disposition — 2026-10-20

The leak and environment re-introduction defects are fixed by the now-closed
`261011-streaming-mode-minimal-fix`. Root-cause descriptions above document
the pre-fix implementation. Only separately tagged stdout/stderr streaming
remains prospective; do not treat this parent as an unfixed environment leak.
Promote that extension when a concrete operator need justifies it.
