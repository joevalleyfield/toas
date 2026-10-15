# Portable Task Capture Paths

Filed as: 261017-task-capture-windows
FKA:
AKA: Windows micro capture path; task capture separators
Legacy index:

keywords: tooling, hardening, compatibility, windows, tasks

Parent: `261015-windows-compatibility-restoration`

Status: CLOSED 2026-10-17

Reproduction: task-capture module has one failure and 32 passes on Windows.
Micro captures return native backslashes instead of the slash-separated relative
paths returned by the other routes. Preserve physical edits, durable capture
records, deduplication, and replay while making the path representation portable.

Existing working-copy changes are prior restoration slices and preexisting
experiment artifacts; this slice only touches task capture and its tracking.

## Result and Evidence

The resolved parent task path now uses as_posix(), consistent with macro and
inbox capture paths. Both the tool response and newly appended durable outcome
use this representation; historical records remain untouched.

- Red: one failure, 32 passes in tests/test_tasks_capture.py.
- Green: 33 passes; targeted toas.tasks coverage is 100% across 492 statements,
  zero missing files. Changed-file Ruff and diff whitespace checks pass.
- Extended the micro test to check the durable outcome path and an idempotent
  repeat: unchanged Markdown and exactly one ledger event.
- Invoked the real capture_task_thread registry tool in an isolated workspace.
  Inspected its JSON response and generated Risks checklist. Response and durable
  event both use tasks/open/5-parent.md; repeat capture remains idempotent.

No full-suite aggregate is inferred from this focused result. Vim harness,
static checks, acceptance completion, and full-spine coverage remain with parent.