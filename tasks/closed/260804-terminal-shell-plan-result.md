Filed as: 260804-terminal-shell-plan-result
FKA:
AKA: nonzero shell result finality; do not retry completed shell commands
Legacy index:

keywords: runtime, implementation, historical, correctness, shell, frontier, recovery

Parent: `260803-first-failure-plan-recovery`
Related: `260803-language-exec-fenced-block-lane`; `260803-tool-intent-ingress-separation`

# Make Completed Non-Zero Shell Results Terminal

## Status

Completed on 2026-08-04.

## Objective

Correct first-failure recovery so a structured-plan shell command that runs to
completion and returns a non-zero exit status becomes the final result. Do not
restage that command and do not execute, promote, or preserve the untouched
suffix as a recovery frontier.

Keep recoverable incomplete tool calls on the existing editable retry plus
staged-suffix lifecycle. Keep sequential explicit user `$` commands on their
separate, non-blocking user-intent path.

## Contract

- A structured plan stops after a completed shell command returns non-zero.
- The shell result remains the final projected consequence.
- No adopted retry or remainder frontier follows that result.
- Any untouched suffix remains visible only in the original durable plan; the
  operator must reconstruct later work after addressing the failure.
- Shell launch/validation failures and recoverable tool-call precondition
  mismatches retain the existing direct retry behavior.
- TOAS does not infer command-specific exit-code vocabularies. Operators can
  use sequential `$` commands when non-zero results should not stop later
  commands.

## Acceptance Criteria

- [x] A successful tool call followed by a completed non-zero shell result
  ends with that result and produces no retry frontier.
- [x] A completed non-zero shell result in the middle of a structured plan
  prevents suffix dispatch and produces no staged suffix.
- [x] A completed non-zero shell retry discards its previously staged suffix.
- [x] Shell launch/validation failures still expose editable recovery.
- [x] Recoverable incomplete non-shell tool calls retain retry/remainder
  behavior.
- [x] Sequential explicit user `$` command behavior remains unchanged.
- [x] Focused and full test suites pass.

## Allowed Write Surfaces

- `src/toas/runtime/step_runtime.py`
- focused runtime and step tests under `tests/`
- this task file and mechanically generated `tasks/WORKBOARD.md`

## Completion Evidence

- Structured-plan recovery now treats a failed shell result with an integer
  `exit_code` as a completed invocation. The result stays final and recovery
  emits neither the command retry nor the untouched suffix.
- Focused tests prove a completed prefix is preserved, a middle/final shell
  failure does not restage, a failed shell retry discards its prior staged
  suffix, and a shell failure without a completed exit still restages.
- An end-to-end `step()` test proves `echo -> pytest(exit 1) -> echo` emits only
  the completed echo and pytest results, with no adopted frontier.
- A separate regression test proves sequential explicit user `$` commands
  continue after a non-zero result.
- Targeted runtime coverage: 350 passed, 100% coverage for
  `toas.runtime.step_runtime`.
- Full suite: 2,813 passed, 9 deselected, 100% coverage.
