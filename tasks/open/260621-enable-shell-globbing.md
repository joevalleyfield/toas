Filed as: 240522-enable-shell-globbing
FKA:
AKA: shell globbing; wildcard expansion; user shell shorthand
Legacy index:

keywords: tooling, investigation, active, compatibility, shell, transcript

# Enable Shell Globbing

## Current Reality

Shell globbing support is only partially implemented.

- The assistant `shell` tool currently expands wildcard characters in `argv`
  with Python `glob.glob(...)` inside
  `src/toas/tools_cluster/shell_ops.py`.
- User-context `$ ...` shell shorthand can reach real shell expansion when the
  original command string is preserved and `needs_shell(...)` routes execution
  through `sh -lc`.
- The task was previously marked closed in prose, but the file remained in
  `tasks/open` and the documented goal overclaimed the current behavior.

## Desired Reality

Shell commands executed through TOAS should have a clear, documented contract
for wildcard expansion.

- If the contract is "real shell behavior", globbing should behave like shell
  expansion rather than a narrow argv post-processing shim.
- If the contract is intentionally narrower for assistant-callable `shell`,
  docs and task history should say so explicitly and avoid claiming "standard
  shell globbing".

## Gap Analysis

- Current assistant-path handling expands `*`, `?`, and `[` in argv tokens, but
  that is not equivalent to full shell evaluation.
- The existing task text conflated user-shell shorthand, assistant `shell`,
  and full shell semantics.
- Task metadata drifted: the filename predates the current `YYMMDD` naming
  scheme and the file status conflicted with its location.

## Known Facts

- `execute_shell_call(..., context="assistant")` validates `argv` and then
  calls `_expand_globs_in_argv(argv)` before subprocess execution.
- `run_user_shell(...)` will execute via `sh -lc` when given a `command`
  string whose content `needs_shell(...)`.
- The original task claimed completion after landing unit coverage for
  glob-triggered routing and end-to-end verification.

## Assumptions

- The remaining user dissatisfaction is about semantic scope, not about the
  bookkeeping alone.
- Preserving search continuity for the old task handle matters more than
  pretending it never existed.

## Unknowns

- Whether assistant-callable `shell` should gain true shell-mediated globbing
  or remain argv-bounded by design.
- Which shell features beyond simple wildcard expansion are actually required
  for the intended user workflows.

## Evidence

- `src/toas/tools_cluster/shell_ops.py`
- `tests/test_tools_shell_ops.py`
- prior task handle: `240522-enable-shell-globbing`

## Decisions

- Rename the task into the current naming scheme.
- Keep the task open until the semantic contract is clarified and matched by
  implementation.
- Record the prior handle in `Filed as:` for continuity.

## Next Actions

- Reproduce the specific globbing cases that still fail or feel incomplete.
- Decide whether the assistant `shell` contract should stay argv-bounded or
  move to shell-mediated execution for wildcard expansion.
- Align docs, tests, and task status with that decision.
