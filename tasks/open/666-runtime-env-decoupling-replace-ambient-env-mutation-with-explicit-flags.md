# 666 Runtime Env Decoupling: Replace Ambient Env Mutation with Explicit Flags
keywords: runtime, implementation, active, correctness, async, env, flags, boundaries

## Goal
Remove legacy runtime dependence on ambient environment-variable mutation in async in-process execution paths, and replace it with explicit typed runtime flags passed through call boundaries.

## Problem
Current async in-process worker flow mutates process-wide environment variables (`os.environ`) to influence streaming behavior and then restores them. This is a holdover from subprocess-heavy architecture and creates hidden coupling, global side effects, and brittle behavior under concurrency.

## Scope
In scope:
- replace runtime-worker env mutation/restore control flow for stream-related behavior with explicit parameters
- thread stream-related flags through runtime call boundaries into shell/llm execution seams
- constrain env reads to true process boundaries (CLI entrypoint/config load), with one-time conversion into typed runtime values
- add/adjust tests to validate behavior via explicit flags, not ambient env state

Out of scope:
- unrelated config-schema redesign
- non-stream env cleanup beyond directly adjacent runtime call paths
- transport/protocol semantic changes

## Initial Plan
1. Introduce explicit stream-control parameters in runtime entry/call paths (e.g. shell stdout stream, LLM stream mode, thinking stream, prompt-progress stream).
2. Propagate these parameters through `start_async_step` -> worker -> `run_step_local`/execution seams.
3. Remove worker-level `os.environ[...]` mutation and restoration for these flags.
4. Keep env parsing at boundary surfaces only (CLI/config/bootstrap) and map once to typed values.
5. Add regression tests asserting effective behavior is determined by passed flags even when ambient env is conflicting.
6. Preserve compatibility at remaining callers with a bounded shim only if needed; document retirement path.

## Progress

- 2026-06-07: Landed a first de-risking slice for shell stdout streaming:
  - `operator_api.step_once`, `cli_session_commands.run_step_local`, `step.step`, and `runtime.step_runtime.run_step` now accept an optional explicit `stream_stdout_enabled` override.
  - `start_async_step` threads the resolved shell stream policy into the in-process operator step instead of relying on `TOAS_STREAM_STDOUT` mutation.
  - `_run_in_process_worker` no longer mutates/restores `TOAS_STREAM_STDOUT`; existing CLI/env-derived behavior remains the default when the explicit override is absent.
  - focused regressions cover explicit override precedence over conflicting ambient env and async worker stdout-env non-mutation.
- 2026-06-07: Landed explicit generation stream-policy threading:
  - `runtime.step_generation_runtime.GenerationRunner` now accepts optional `stream_stdout_enabled`, `stream_thinking_enabled`, and `stream_prompt_progress_enabled` values, falling back to env only when those explicit values are absent.
  - `operator_api.step_once` and `cli_session_commands.run_step_local` thread thinking/prompt-progress policy alongside stdout policy for async in-process execution.
  - `start_async_step` now passes resolved thinking/progress stream policy to the operator step and only installs reasoning/progress callbacks when the policy enables those lanes.
  - `_run_in_process_worker` no longer mutates/restores `TOAS_STREAM_THINKING` or `TOAS_STREAM_PROMPT_PROGRESS`.
  - focused regressions cover explicit generation policy precedence over conflicting ambient env and worker non-mutation for all three stream flags.
- 2026-06-07: Landed explicit LLM stream-mode threading for async in-process execution:
  - `GenerationRunner` now accepts an optional `llm_stream_mode` override and applies it to selected backend/model settings before generation.
  - `operator_api.step_once` and `cli_session_commands.run_step_local` thread the override to the runner.
  - `start_async_step` passes `llm_stream_mode="enabled"` instead of mutating `TOAS_LLM_STREAM_MODE`, preserving the old in-process streaming behavior while avoiding global env side effects.
  - focused regressions cover override precedence over ambient `TOAS_LLM_STREAM_MODE` and worker non-mutation.
- 2026-06-07: Landed runner-level prompt-progress debug policy threading:
  - `GenerationRunner` now accepts optional `debug_prompt_progress_enabled` and `debug_prompt_progress_file` values for prompt-progress summary diagnostics.
  - `operator_api.step_once` and `cli_session_commands.run_step_local` thread those values explicitly.
  - `start_async_step` reads the debug env knobs once at async-step entry and passes typed values onward; the worker no longer relies on ambient env for runner-level prompt-progress summary diagnostics.
  - focused regressions cover explicit debug policy precedence over conflicting ambient env.

Remaining scope:
- final cleanup/contract pass proving `_run_in_process_worker` no longer mutates stream-control env keys;
- extend parity coverage to LLM/reasoning/progress streaming after those flags move off ambient env, if current focused coverage is not enough for closure.

## Follow-up Parking Lot

- Consider consolidating the older `GenerationRunner` definition still present in `cli_session_commands.py`; active construction now comes from `runtime.step_generation_runtime`, but the duplicate class keeps lint noise and reader confusion alive.
- Lower-level transport debug reads in `llm.py` (`TOAS_DEBUG_PROMPT_PROGRESS`, `TOAS_DEBUG_PROMPT_PROGRESS_FILE`, and adjacent stream debug flags) remain ambient diagnostic env reads; decide separately whether those should become typed transport debug policy.

## Technical Targets
- `src/toas/runtime/async_step_runtime_worker.py`
- `src/toas/cli.py` / `src/toas/cli_session_commands.py` / `src/toas/step.py` seams as needed for explicit flag threading
- stream/shell execution seams currently keyed off `TOAS_STREAM_STDOUT` and related stream env toggles

## Done When
- async in-process worker no longer mutates process env for stream-control flags
- behavior parity retained for local-host async shell-intent and LLM-like streaming flows
- focused regression tests fail under old ambient-env coupling and pass under explicit-flag control
- roadmap/task status updated with landed scope and any explicit follow-on cleanup slices

## Risks / Notes
- some current helper seams may still derive behavior from env reads; work should make dependency direction explicit (boundary -> typed runtime -> execution), avoiding partial dual-authority drift.
- preserve existing user-facing defaults while removing hidden global mutation.

## Related
- `665` shell-intent streaming backslide fix
- `534` local-first async default policy and cutover controls
- `660` shell lane spawn-semantics unification follow-up
