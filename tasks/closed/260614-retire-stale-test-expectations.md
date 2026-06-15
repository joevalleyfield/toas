Filed as: 260614-retire-stale-test-expectations
FKA:
AKA: skipped tests; xfail cleanup; stale test expectations; test-suite hygiene
Legacy index:

keywords: tooling, hardening, historical, contract, tests, coverage, vim, frontier

# Retire Stale Test Expectations

## Current Reality

The full suite still reported one unconditional skip and one xfail after the 100% coverage ratchet landed.

- `tests/test_vim_driver_phase6_viability_report.py` skipped unconditionally because the phase-6 viability precursor was superseded by current host/transport contract coverage.
- `tests/test_cli.py::test_run_step_local_interaction_lag_evolution_target_behavior` was a non-strict xfail for a desired frontier boundary contract, but its probe was stale and failed before reaching the intended assertion when `bind_parent` was `none`.
- After retiring those expectations, two `tests/test_cli_demo_async_client.py` warnings remained visible: a `runpy` warning from executing an already-imported module as `__main__`, and an unawaited coroutine warning from using `AsyncMock` for a synchronous async-stdin `write` method.

## Desired Reality

The normal suite should not carry historical skip/xfail noise when the expectation is no longer an active gate.

## Decisions

- Retired the collected phase-6 viability report test rather than keeping an unconditional skip. Historical context remains in closed task `555`, while active Vim/host behavior authority remains with current host and transport contract tests.
- Retired the stale frontier-boundary xfail rather than preserving a decorative failing memory. Nearby passing tests still cover the current rewritten-tail consequence behavior, and future work should reopen a focused task with a fresh repro if the stricter boundary-lag target becomes active again.
- Tightened `tests/test_cli_demo_async_client.py` to remove warning noise: the `runpy` main-path test now evicts only the target module before execution, async stdin mocks now match the real synchronous `write` / async `drain` shape, and real subprocess tests explicitly close their pipes.

## Evidence

- `pytest --runxfail` showed the xfail still failed, but through stale instrumentation rather than a clean target assertion.
- The skipped Vim test identified itself as superseded by current host/transport contract coverage.
- `tests/test_cli_demo_async_client.py` passes with warnings promoted to errors.

## Outcome

The skip, xfail, and exposed warning noise were removed from collected tests.
