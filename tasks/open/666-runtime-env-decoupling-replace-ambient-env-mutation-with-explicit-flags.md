# 666 Runtime Env Decoupling: Replace Ambient Env Mutation with Explicit Flags

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
