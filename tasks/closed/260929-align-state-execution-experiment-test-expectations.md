Filed as: 260929-align-state-execution-experiment-test-expectations
FKA:
AKA: state execution experiment test alignment
Legacy index:

keywords: experiments, test, state-execution, active

Parent: `260926-state-experiment-plan-tools`
Related: `260926-state-experiment-harness`

# Align State Execution Experiment Test Expectations

## Intent

Update test assertions in `tests/test_state_execution_experiment.py` to match the
tool execution observation formats introduced by planned and reviewed tools
(`8f066ba6`).

## Acceptance Criteria

- `test_invalid_response_retried_and_action_failure_is_observed` expects tool
  failure observations formatted as `Tool <n> (<type>) failed: ...` and captures
  the specific tool error.
- `test_empty_continuation_does_not_replay_previous_result` checks that `continue`
  produces its continuation observation header rather than replaying previous inspect
  results, without strict equality to empty string.
- All tests in `tests/test_state_execution_experiment.py` pass.

## Progress

- 2026-09-29: Opened task and updated test assertions in `tests/test_state_execution_experiment.py`
  to match `Tool 1 (<type>) failed:` format and continuation header output. All 22 tests
  in `test_state_execution_experiment.py` and all 3355 tests in the repo pass cleanly.

Status: Complete.
