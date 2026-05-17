# 533 Local Async Lifecycle Functional And System Assertions

## Goal
Add higher-level system/functional assertions that verify local async lifecycle behavior (`step --async`, `watch`, `cancel`) beyond unit seam tests.

## Why
`532` landed local lifecycle paths and preserved default RPC behavior, but we still need stronger integration confidence that these paths behave correctly end-to-end at daemon/runtime and acceptance-facing boundaries.

## Scope
In scope:
- extend daemon/runtime integration tests for local async lifecycle progression/terminality
- add at least one functional/acceptance-style assertion path for local async backend mode
- verify envelope/status/chunk contracts remain stable under local backend mode
- keep test runtime pragmatic (prefer targeted and deterministic assertions)

Out of scope:
- new runtime architecture changes
- daemon removal
- transport redesign

## Done When
- local async lifecycle behavior has system/functional assertions beyond unit-only coverage
- tests validate stable operator-facing lifecycle contracts under local mode
- full suite passes

## Related
- `525` post-envelope runtime ownership and primary-path de-daemonization
- `532` local async execution path implementation

## Progress
- implemented first validation slice:
  - added CLI-level local async lifecycle contract assertion covering:
    - `run_step_async` local mode status line contract
    - `run_watch` local mode poll contract
    - `run_cancel` local mode status line contract
  - assertion verifies local mode routes `step --async`/`watch`/`cancel` without RPC calls and preserves operator-facing output shape
  - validated with:
    - `uv run pytest -q tests/test_cli.py --no-cov`
    - `uv run pytest -q -n 14`
- implemented second validation slice:
  - added daemon/runtime integration assertion for local async lifecycle:
    - starts async run via in-process async start path
    - exercises cancel path and verifies lifecycle envelope contract
    - follows watch until terminal and verifies terminal envelope (`llm_done`) presence when envelopes are present
  - this extends coverage beyond unit seam mocks into runtime lifecycle progression/terminality behavior
  - validated with:
    - `uv run pytest -q tests/test_cli.py tests/test_daemon.py --no-cov`
    - `uv run pytest -q -n 14`
