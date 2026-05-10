# 504 Coverage Missing-Files Ratchet Gate

## Objective
Add a second coverage gate that fails when too many files are below 100% coverage, so we can ratchet file-completeness alongside the existing percentage gate.

## Why
Global percent alone hides noisy long-tail regressions. A missing-files cap provides a simple, observable ratchet (e.g., current baseline 28) and drives steady elimination of partially covered files.

## Scope
- add pytest CLI option for max allowed count of files below 100%
- compute missing-file count from coverage data at session end
- fail test run when count exceeds configured cap
- document usage and add focused tests for counting/gate behavior

## Done When
- `pytest --cov-max-missing-files=N` enforces the cap
- default behavior unchanged when option omitted
- tests cover counting and threshold evaluation

## Related
- `374` coverage-led refactor pass
- `379` coverage noise burndown

## Progress
- ratcheted coverage missing-files cap from `20` to `19` in `pyproject.toml`
- added replay-runner branch/error-path tests to move `src/toas/replay_runner.py` to full coverage and satisfy the new cap
- ratcheted coverage missing-files cap from `19` to `18` in `pyproject.toml`
- ratcheted coverage missing-files cap from `18` to `17` in `pyproject.toml`
- added `--cov-max-missing-files` pytest option in `tests/conftest.py`
- added session-end gate that reads `.coverage` and fails if files below 100% exceed cap
- added `src/toas/coverage_gate.py` with `coverage_file_stats()` helper
- added `tests/test_coverage_gate.py` for direct counting behavior
- set initial ratchet baseline in `pyproject.toml` addopts: `--cov-max-missing-files=28`
- ratcheted baseline from `28` to `27`
- hardened gate behavior for targeted runs: skip missing-files check when pytest-cov is disabled (`--no-cov`)
- added direct analysis-command test coverage for missing second-head branch:
  - `tests/test_cli_analysis_commands.py::test_run_diff_local_raises_when_head_b_missing`
- full-suite validation after ratchet: `1365 passed`, `94.29%`
- changed missing-files gate failure mode to defer until terminal summary so normal coverage report still prints
- ratcheted baseline from `27` to `26`
- ratcheted baseline from `26` to `25`
- added focused config parsing tests to cover unknown section/field key resolution paths
- full-suite validation with xdist: `uv run pytest -q -n 14` passes at cap `25`
- ratcheted baseline from `25` to `24`
- added focused runtime intent-arbitration coverage for YAML parse-error tolerance in `yaml_position=any` path
- full-suite validation with xdist: `uv run pytest -q -n 14` passes at cap `24`
- ratcheted baseline from `24` to `23`
- removed unreachable pending-flush fallback branch in `shell_streaming` and revalidated behavior tests
- full-suite validation with xdist: `uv run pytest -q -n 14` passes at cap `23`
- ratcheted baseline from `23` to `22`
- added focused session-view behavior assertions (`run_session_path_local`, prompt-list rendering with and without category metadata)
- full-suite validation with xdist: `uv run pytest -q -n 14` passes at cap `22`
- added deterministic `rpc_unix` `_serve_connection` branch tests to remove one-file ratchet flakiness under xdist
- ratcheted baseline from `22` to `21`
- full-suite validation with xdist: `uv run pytest -q -n 14` passes at cap `21`
- ratcheted baseline from `21` to `20`
- full-suite validation with xdist: `uv run pytest -q -n 14` passes at cap `20`
