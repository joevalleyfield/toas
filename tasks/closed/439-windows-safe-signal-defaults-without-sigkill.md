# 439: Windows-safe signal defaults without `SIGKILL`

## Summary
Remove or guard any default argument usage that assumes `signal.SIGKILL` exists, so Windows runtimes do not fail at import or call time.

## Problem
At least one default argument currently references `signal.SIGKILL`. On Windows, `SIGKILL` is not defined, which can cause failures when evaluating defaults or executing affected code paths.

## Goals
- Ensure TOAS imports and runs on Windows without referencing missing signal constants.
- Preserve existing POSIX behavior where `SIGKILL` is available and intended.
- Keep signal-handling logic explicit and test-backed across platform branches.

## Proposed Direction
- Locate default argument bindings (and other unconditional references) to `signal.SIGKILL`.
- Replace default-time constant capture with runtime-safe selection logic.
- Prefer platform-safe fallbacks (for example `SIGTERM`/`CTRL_BREAK_EVENT` as appropriate to call site semantics) while preserving existing POSIX intent.
- Add tests that validate behavior when `SIGKILL` is unavailable.

## Acceptance Criteria
- No import-time or runtime failures occur on Windows due to missing `signal.SIGKILL`.
- POSIX behavior remains unchanged for existing `SIGKILL`-using paths where available.
- Tests cover both availability and unavailability branches for the chosen signal default behavior.

## Notes
- Keep this task focused on default/signature safety and immediate call-site compatibility.
- Any broader process-control redesign should be split into a separate task.
