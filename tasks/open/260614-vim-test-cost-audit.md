## Goal
Filed as: 260614-vim-test-cost-audit
FKA:
AKA: vim tests; test suite cost; stdio contract tests; test performance
Legacy index: 688

keywords: vim, test, cost, performance, optimization, stdio, contract

Audit the vim driver test suite to determine whether the tests are as cheap as they could be given what they're actually verifying.

## Why Now

The vim tests dominate suite wall-clock time. Before accepting that cost as necessary, we should verify that the test structure isn't paying for setup/teardown or subprocess overhead that exceeds what the assertions actually require.

## Scope

- Profile which vim test files/cases consume the most time (`pytest --durations=20`)
- For the slowest tests, examine what they're actually asserting vs. what infrastructure they spin up
- Ask: could the same behavioral guarantee be achieved with a lighter fixture (mock subprocess, in-process call, smaller event sequence)?
- Identify any tests that are sleeping or using fixed timeouts where event-driven waits would suffice
- Flag tests that are acceptance-adjacent in cost but not marked `acceptance` (and thus always run)

## Out of Scope

- Changing what is verified, only how cheaply it can be verified
- Vim driver behavior changes

## Done When

- A short written summary of where the time goes and which tests (if any) have optimization headroom
- Any quick wins landed; slower restructuring logged as follow-on tasks
