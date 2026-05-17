# 529 Acceptance Marker Contract And Slow Non-Acceptance Audit

## Objective
Make acceptance-vs-default test lane boundaries explicit and reliable, then audit slow non-acceptance tests so fast-lane runtime is intentional.

## Why
- Current default filtering uses `-m "not acceptance"`, but acceptance-step tests are not marker-tagged, so they leak into the default lane.
- Ad hoc `-k "not acceptance"` appears faster mainly because of keyword/path matching side effects, not a durable policy.
- We need marker-driven policy plus a clear view of genuinely slow unit/light integration tests.

## Scope
- Add acceptance marker wiring for the acceptance suite (`tests/acceptance/**`).
- Validate lane separation using collection/count and duration comparisons.
- Produce an inventory of slow non-acceptance tests (top offenders) for follow-on optimization work.
- Keep this as test-lane hygiene; do not refactor runtime code in this task.

## Survey Findings (2026-05-16)
- Acceptance test modules:
  - `tests/acceptance/steps/test_complete_change_request_steps.py`
  - `tests/acceptance/steps/test_control_lane_multi_command_frontier_steps.py`
- `-m "not acceptance"` currently still runs acceptance steps due to missing marker annotations.
- Slow non-acceptance tests (~1s each) are concentrated in shell/subprocess behavior tests, e.g.:
  - `tests/test_tools.py` shell command behavior tests
  - `tests/test_step.py` user shell/callable shell lane tests
  - `tests/test_shell_streaming.py::test_run_streaming_subprocess_collects_stdout`
  - `tests/test_daemon_backend_lifecycle.py::test_managed_backend_start_health_fail`

## Done When
- Acceptance suite is marker-tagged so `-m acceptance` and `-m "not acceptance"` are semantically correct.
- We have an explicit slow non-acceptance inventory in this task file with recommended follow-on grouping.
- Roadmap reflects this as active test-lane hygiene work.

## Initial Plan
1. Apply `pytest.mark.acceptance` at package/module level under `tests/acceptance`.
2. Re-run collection and duration checks for lane proof.
3. Record top slow non-acceptance cases and propose follow-on slices (likely under recurring `505` + coverage ratchet cadence).

## Progress (2026-05-16)
- Added acceptance suite marker wiring in `tests/acceptance/conftest.py` via collection-time path-scoped marking:
  - marks only items under `/tests/acceptance/`.
- Lane proof (with `-o addopts=''` to avoid default-filter interference):
  - `-m acceptance`: `9` collected
  - `-m "not acceptance"`: `1554` collected
  - total: `1561` collected
- Runtime proof (`-m "not acceptance"`, `-n 14`):
  - `1552 passed in 8.54s`
  - acceptance-step tests no longer appear in slowest-duration list.
- Slow non-acceptance inventory (top recurring ~1s tests) is now clearly separated and concentrated in shell/subprocess behavior:
  - `tests/test_daemon_backend_lifecycle.py::test_managed_backend_start_health_fail`
  - `tests/test_shell_streaming.py::test_run_streaming_subprocess_collects_stdout`
  - multiple shell-lane tests in `tests/test_step.py`, `tests/test_tools.py`, `tests/test_tools_shell_ops.py`, and one in `tests/test_cli.py`.

## Follow-on Recommendations
- Route slow non-acceptance optimization into recurring `505` (function-intent test audit) with a speed-focused slice:
  - prefer fixture/setup consolidation and subprocess test-shape tightening before behavioral reduction.
- Keep `-m` as contract selection (`acceptance` vs `not acceptance`) and use `-k` only for ad hoc local targeting.
