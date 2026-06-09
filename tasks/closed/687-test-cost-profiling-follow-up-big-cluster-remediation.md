# 687 Test Cost Profiling Follow-up: Big Cluster Remediation

keywords: tests, performance, profiling, runtime, stdio, vim, timeout, fixtures, historical

## Goal

Go after the remaining expensive test clusters identified in task 680, either by faking at a narrower seam or by seeing if the test's actual goal can be accomplished less slowly.

## Why

Task 680 remediated the ~24 shell routing tests (from ~25s to ~1s), but 49s of call time remains across 56 tests. The biggest lever is the stdio pacing test at 19s. If even some of these can be faked or made faster, the suite runs much tighter.

## Current Cluster Breakdown

### Tier 1: stdio pacing/cancel/stream (24.5s, 8 tests)

| Time | Test | What it validates |
|------|------|-------------------|
| 19.0s | `test_runtime_host_stdio_llm_standin_integration.py::test_host_stdio_user_lane_tool_pacing_shape` | Stream-lane composition with pacing delays |
| 1.1s | same file :: `test_host_stdio_with_llm_standin_cancel_stream_shape` | Cancel mid-stream |
| 1.0s | same file :: `test_managed_backend_start_health_fail` | Backend startup failure path |
| 0.87s | same file :: `test_host_stdio_with_llm_standin_cancel_stream_shape_time_ally` | Cancel timing |

**Question:** Can the stream-lane composition be proven with a synchronous fake for the LLM standin, without the pacing delays? The 666 fixture pattern (real composition above `GenerationRunner`, fake generation below) might apply here.

### Tier 2: Vim process (13.3s, 5 tests)

| Time | Test | What it validates |
|------|------|-------------------|
| 11.4s | `test_vim_driver_phase2_async.py::test_vim_driver_phase2_async_smoke` | Vim async driver |
| 0.61s | `test_vim_driver_contract_plugin.py::test_contract_plugin_burst` | Contract burst |
| 0.37s | same file :: `test_contract_plugin_baseline` | Contract baseline |
| 0.32s | `test_vim_driver_phase3_job_channel_isolated.py::test_vim_driver_phase3_job_channel_isolated` | Job channel isolation |
| 0.32s | `test_vim_driver_baseline.py::test_vim_driver_baseline_smoke` | Baseline smoke |

**Question:** Vim is the thing under test — hard to fake. But are these tests paying startup/teardown cost on every invocation? Could a shared Vim instance or faster teardown help?

### Tier 3: timeout waits (6.3s, 10 tests)

| Time | Test | What it validates |
|------|------|-------------------|
| 2.0s | `test_cli_demo_async_client.py::TestRunDemoAsyncStdio::test_subscribe_timeout_returns_3` | Subscribe timeout |
| 0.75s × 6 | `test_runtime_session_host_process.py` — 6 subscribe/timeout tests | Subscribe machinery handles incomplete streams |
| 0.10s × 2 | `test_cli_demo_async_client.py` — 2 timeout tests | Timeout returns |

**Question:** For the 0.75s × 6 cluster, can a partial stream be injected without waiting for the timer? For the 2.0s subscribe timeout, is there a way to make the timeout shorter in the test?

### Tier 4: subprocess lifecycle (4.3s, 8 tests)

| Time | Test | What it validates |
|------|------|-------------------|
| 1.05s | `test_daemon_async_runner.py::test_integration_subprocess_path_emits_tool_progress_and_terminal_event` | Subprocess lifecycle with progress |
| 1.04s | `test_daemon_backend_lifecycle.py::test_managed_backend_start_health_fail` | Backend startup failure |
| 1.03s | `test_shell_streaming.py::test_run_streaming_subprocess_collects_stdout` | Streaming I/O |
| 0.53s | `test_daemon.py::test_local_async_lifecycle_contract_step_watch_cancel` | Subprocess startup |
| 0.11s | `test_daemon_backend_lifecycle.py::test_managed_backend_start_breaks_when_process_exits_before_health` | Process exit before health |

**Question:** These are genuinely testing subprocess startup/teardown — the thing under test. But can the startup be faked with a faster process (e.g., `echo` instead of a real backend)?

## Progress

- **Subscribe timeout cluster** (6 tests): 0.75s each → 0.05s each via `TOAS_HOST_SUBSCRIBE_DEADLINE_CAP_S=0.05`. The synchronous daemon mock caused the subscribe loop to spin 35k+ times in 0.75s; reducing the cap to 0.05s makes the loop exit 15x faster.
- **Early exit check** in `session_host_process.py`: added deadline check BEFORE spawning the thread, preventing unnecessary thread spawning when deadlines have already passed.
- **Stdio pacing test**: 19s → 3s. Reduced iterations from 120 to 20, reduced subscribe loop idle timeouts from 6×3.0s to 2×1.0s.
- **Subscribe timeout test**: 2.18s → 1.31s via shorter `read_timeout_s=0.1`.
- **Vim phase2 async test**: 11.3s → 1.9s. Root cause: `child.isalive()` polling loop. pexpect doesn't reap the child until `expect()` is called, so `isalive()` returns True even after process death. The while loop slept the full timeout. Replaced with `child.expect(pexpect.EOF)` which correctly detects process exit. Also removed the `script -q /dev/null` wrapper — vim starts in ~270ms on its own via pexpect.
- **Cancel stream tests** (2 tests): 0.77s + 0.79s → 0.32s + 0.31s. Root cause: `ThreadingHTTPServer.serve_forever()` uses a default `poll_interval=0.5s` for its select loop. When `shutdown()` is called, it sets a flag and waits for the server loop to notice — which can take up to 500ms. Fix: pass `poll_interval=0.01` to `serve_forever()`. The test body is actually ~310ms; the remaining 460ms was teardown.
- **EOF bug in shell_streaming.py**: `_read_into_pending` now returns `True` on `os.read()` returning `b""` (EOF), breaking the infinite loop. Fixed 3 subprocess tests from ~1s each to ~0.02-0.04s.
- **max(1.0, health_timeout_s) floor** in `backend_lifecycle.py`: removed the `max(1.0, ...)` constraint, reducing `test_managed_backend_start_health_fail` from 1.05s to 0.21s.
- **Subscribe timeout** in `cli_demo_async_client.py`: `_run_demo_async_stdio` now calculates `remaining` time before blocking on `q.get()`, reducing `test_subscribe_timeout_returns_3` from 1.10s to <0.01s.
- **Subprocess sleep** in `test_local_async_lifecycle_contract_step_watch_cancel`: reduced from 0.25s to 0.05s, improving from 0.55s to 0.31s.
- **Vim delay** in `test_vim_driver_phase2_async.py`: reduced from 700ms to 100ms, test from 1.96s to 1.33s.

Suite: 22.6s → 13.1s → 11.7s → 10.0s → 8.21s (64% reduction). 2013 passed.

## Scope

- for each cluster, determine whether the test goal can be achieved less slowly
- prefer faking at the narrowest seam that still proves the behavior
- if a test genuinely needs the slow path, document why and consider whether a faster subset test covers the happy path
- use the `fake_shell_subprocess` pattern as a model: fake below the semantic boundary, keep the composition above it real

## Non-Goals

- weakening integration coverage
- removing tests that validate real subprocess/stdio/Vim contracts
- broad test-suite restructuring without measured payoff

## Done When

- [x] each cluster has been evaluated: either remediated or documented as genuinely requiring the slow path
- [x] at least two clusters show measurable improvement
- [x] the timing profile is updated with the new baseline

## Cluster Status

- **Tier 1 (stdio pacing/cancel/stream)**: Cancel stream tests done (0.77s → 0.32s via LLM server shutdown fix). Stdio pacing test (0.50s) is shell-based with 20×10ms sleeps — hard to reduce further without changing semantics.
- **Tier 2 (Vim process)**: Phase2 async test done (1.34s, vim startup ~270ms dominates). Contract plugin tests (0.58s + 0.29s) also vim startup bound. Cannot fake — vim is the thing under test.
- **Tier 3 (timeout waits)**: Done. Subscribe timeout cluster done via deadline cap. Subscribe timeout test done via remaining-time check.
- **Tier 4 (subprocess lifecycle)**: Done. EOF bug fix, health_timeout floor removed, sleep reduced.
