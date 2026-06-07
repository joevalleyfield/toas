# 680 Test Cost Profiling and Millisecond Boundary Remediation
keywords: tests, performance, profiling, runtime, streaming, subprocess, fixtures, parked

## Goal

Create a repeatable test-cost profiling and remediation lane so expensive tests are intentional, visible, and pushed toward millisecond-scale fakes unless they are literally validating slow streaming, subprocess, stdio, Vim, or timeout behavior.

## Why

Task `666` needed a high-level async/generation proof, but that proof should not require live LLMs, real streaming latency, subprocess sleeps, or multi-second timing. A timing pass showed the suite has a small number of obviously expensive integration tests plus a broader band of ~1s shell/subprocess tests that may be paying real process/timing cost where a narrower fake would prove the behavior.

Fresh timing snapshot from 2026-06-07:

```bash
./.codex-local/bin/uvt run pytest -n 14 -q --no-cov --durations=40 --durations-min=0 --junitxml=/tmp/toas-pytest-times.xml
```

Result:
- wall time: 22.60s
- JUnit summed testcase time: ~75.3s
- outcome: 1977 passed, 1 skipped, 1 xfailed

Top individual costs:
- 19.09s `tests/test_runtime_host_stdio_llm_standin_integration.py::test_host_stdio_user_lane_tool_pacing_shape`
- 11.30s `tests/test_vim_driver_phase2_async.py::test_vim_driver_phase2_async_smoke`
- 2.01s `tests/test_cli_demo_async_client.py::TestRunDemoAsyncStdio::test_subscribe_timeout_returns_3`
- ~1.0s cluster across shell/subprocess tests in `tests/test_step.py`, `tests/test_tools.py`, `tests/test_tools_shell_ops.py`, `tests/test_cli.py`, `tests/test_shell_streaming.py`

Top cumulative file costs:
- 21.05s `tests/test_runtime_host_stdio_llm_standin_integration.py`
- 13.84s `tests/test_step.py`
- 11.30s `tests/test_vim_driver_phase2_async.py`
- 7.42s `tests/test_tools.py`
- 4.52s `tests/test_runtime_session_host_process.py`

## Scope

- add or document a repeatable timing collection workflow using existing pytest/JUnit facilities
- classify expensive tests into:
  - justified slow integration/timing tests
  - tests that should stay end-to-end but can use synchronous fakes
  - tests that should move down a seam and avoid subprocess/sleep cost
- remediate high-cost tests where a narrower fake preserves proof quality
- prefer mocking immediately below the semantic boundary under test, not above it
- keep proof of stream-lane composition in milliseconds unless the test is explicitly validating slow generation or timeout behavior

## Non-Goals

- weakening coverage by replacing all integration tests with unit tests
- removing the few slow tests that genuinely validate timing, cancellation, stdio, Vim, or subprocess contracts
- broad test-suite restructuring without measured payoff

## Progress

- Created `tests/test_cost_profile.md` with timing workflow and test classification
- Created `fake_shell_subprocess` fixture in `tests/conftest.py` that patches
  `toas.tools_cluster.shell_ops.run_subprocess` with a side_effect that echoes
  argv/cwd back into the result dict
- Applied fixture to shell routing tests across:
  - `test_tools.py` (7 tests): 7.83s → 0.27s
  - `test_tools_shell_ops.py` (2 tests)
  - `test_step.py` (12 tests): ~12s → ~0.34s
  - `test_cli.py` (3 tests)
- Adjusted assertions to validate routing semantics (argv, cwd, env) instead
  of actual subprocess output
- Remaining slow tests are classified as justified (stdio, Vim, timeout,
  streaming I/O, subprocess lifecycle)

## Done When

- [x] there is a checked-in timing/profiling workflow or script/report note that can be rerun
- [x] the current slowest tests are classified with rationale
- [x] at least one unjustified expensive cluster is remediated or split into a fast semantic fixture plus a smaller slow contract test
- [x] follow-up slow tests, if any remain, are documented with why they are allowed to stay slow

## Outcome

Closed 2026-06-07. All four done-when items satisfied.

The ~24 shell routing tests across `test_tools.py`, `test_tools_shell_ops.py`,
`test_step.py`, and `test_cli.py` were paying subprocess fork cost to prove
command routing semantics (argv construction, cwd resolution, env passing).
These are now faked at the `shell_ops.run_subprocess` seam via the
`fake_shell_subprocess` fixture, bringing that cluster from ~25s of call
time down to ~1s.

The remaining big ones are genuinely validating the things they're named for:
stdio pacing/cancel (24.5s), Vim process (13.3s), timeout contracts (6.3s),
subprocess lifecycle (4.3s). Those are the "literally validating" cases the
goal says to keep.

One notable follow-up: the 0.75s × 6 subscribe timeout cluster in
`test_runtime_session_host_process.py` (4.5s total) is worth another look —
if a partial stream can be injected without waiting for the timer, that's
a real win. But that's a different seam and belongs to a subsequent task.

## Notes

- Use `pytest -n 14` for full-suite timing by default, plus JUnit parsing for per-test aggregation.
- For per-test call duration precision, a serial run can be useful, but full-suite wall-clock should be measured with the normal parallel setting.
- The `666` high-level async/generation fixture is the model: real composition above `GenerationRunner`, fake generation below it, no sleeps, no live backend, no stdio host.
