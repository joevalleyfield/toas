# 440: Disallowed assistant tool auto-stage regression

## Summary
Restore behavior where disallowed assistant tool calls are automatically staged into the user turn rather than being dropped or left inert.

## Problem
Current behavior appears regressed: disallowed assistant tools are not being auto-staged into the user turn as expected. This breaks the intended assistant-to-user intent handoff in the shell authorization flow.

## Goals
- Reproduce and lock the regression with deterministic tests.
- Restore auto-staging behavior for disallowed assistant tools.
- Preserve existing authorization and durable-history invariants.

## Proposed Direction
- Trace the disallowed-tool branch in the shell authorization/staging path tied to umbrella `328` (`331`-`333` surfaces).
- Add a focused regression test that asserts disallowed assistant tool attempts produce the expected staged user-turn artifact.
- Patch the staging path where the handoff was lost, keeping durable record semantics unchanged.

## Acceptance Criteria
- Disallowed assistant tool attempts are auto-staged into the user turn again.
- The staged output shape matches existing shell/user-intent contracts.
- Tests cover both allowed and disallowed branches to prevent recurrence.

## Notes
- Keep this as an explicit regression task rather than bundling into umbrella execution notes.

## Progress
- 2026-04-24: Added reproduction coverage in `tests/test_step.py` for assistant `shell_script` disallow auto-stage behavior (`xfail`, strict) to lock the current regression before implementation work.
