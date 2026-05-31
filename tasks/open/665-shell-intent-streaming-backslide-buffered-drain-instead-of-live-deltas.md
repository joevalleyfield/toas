# 665 Shell Intent Streaming Backslide: Buffered Drain Instead of Live Deltas

## Goal
Track and fix a regression where direct shell-intent runs (notably many back-to-back `$ cat ...` lines) do not emit timely live stream deltas, and instead appear as delayed buffered output that is drained later.

## Bug Summary
Observed behavior in `.toas/foo.md` scenario:
- transcript contains many consecutive lines beginning with `$ cat ...`
- run appears quiet for an extended period (repeated subscribe idle timeouts)
- output then appears in chunks (looks streamed) but is likely delayed projection drain of buffered content

This is a backslide from expected live streaming semantics.

## Repro Context
- local host stdio path
- file: `.toas/foo.md`
- input pattern: large burst of consecutive shell intent lines (`$ cat ...`)
- logs showed repeated `push_complete complete=false reason=idle_timeout` before eventual terminal completion and chunked render/apply

## Expected Behavior
- bounded time-to-first-visible-output for long direct shell-intent runs
- incremental deltas should arrive while commands are executing (not only after buffered completion)
- no prolonged idle-timeout loop when meaningful stdout is being produced upstream

## Actual Behavior
- prolonged idle-timeout subscribe churn before first meaningful visible output
- eventual output arrives and is rendered in chunks due to apply-budget path, creating "fake streaming" from buffered backlog

## Scope
In scope:
- identify where shell-intent path loses incremental event emission
- restore true live delta emission semantics for direct user shell-intent bursts
- add regression tests for bounded first-event latency and non-buffered progression

Out of scope:
- unrelated cancel lifecycle behavior
- general model token streaming policy changes

## Done When
- repro scenario no longer exhibits long silent window before first output
- logs show incremental semantic events during command execution
- regression tests cover this pattern and fail on buffered-drain-only behavior

## Related
- `534` local-first async policy/cutover controls
- `664` cancel/pathing progression log (separate but adjacent investigation)

## Progress (2026-05-31)
- Reopened after initial close because real Vim path still showed buffered-drain feel under high-volume tool-lane output.
- Confirmed and fixed workdir/pathing confusion in local-host cancel payload handling.
- Identified and fixed plugin default collision that forced `g:toas_watch_apply_bytes_per_tick=512` (duplicate default blocks); apply budget now resolves to intended higher value unless explicitly overridden.
- Added user-lane pacing instrumentation and integration coverage:
  - `tests/test_runtime_host_stdio_llm_standin_integration.py` (tool-lane pacing scenario)
  - `src/toas/runtime/stream_pacing_summary.py` + `tests/test_runtime_stream_pacing_summary.py`
- Added runtime tool-lane batching knobs (`TOAS_TOOL_STREAM_FLUSH_BYTES`, `TOAS_TOOL_STREAM_FLUSH_MS`) and benchmarked gradient near 42ms budget.
- Current evidence:
  - apply-cap bottleneck at `512` is removed
  - throughput improves with larger tool flush byte caps up to ~`64k` in saturated 2s window tests
  - remaining limiter in real Vim path is subscribe-window churn (`push_complete complete=false reason=request_deadline`) plus long watch tick durations under heavy load
- Next likely slice (if continued): keep sub-second control responsiveness but reduce forced rollover churn on active progress windows.

## Resolution
- Root cause identified in `src/toas/runtime/async_step_runtime_worker.py`: cold in-process worker hard-set `TOAS_STREAM_STDOUT=0`, which disabled live shell stdout streaming for direct user shell-intent execution and produced delayed buffered drain behavior.
- Fix landed: worker now applies resolved shell stream policy (`shell_stream_enabled`) and sets `TOAS_STREAM_STDOUT` to `1`/`0` accordingly.
- Signature plumbing updated so `start_async_step` passes resolved policy into both sync and asyncio worker paths.
- Regression coverage added in `tests/test_daemon_async_runner.py` to assert worker env policy application (`TOAS_STREAM_STDOUT` value seen inside `cli_run_step_local_fn`), and all updated async-runner tests pass.

## Validation
- `uv run pytest tests/test_daemon_async_runner.py -q --no-cov`
- Result: `26 passed`
