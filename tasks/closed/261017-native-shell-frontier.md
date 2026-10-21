# Native Windows Shell Frontier Verification

Filed as: 261017-native-shell-frontier
FKA:
AKA: Windows echo launch; direct argv portability; shell frontier parity
Legacy index:

keywords: runtime, hardening, compatibility, windows, shell, frontier

Parent: `261015-windows-compatibility-restoration`
Related: `261015-selectable-shell-runtime`; `261015-shell-launcher-reader-portability`

Status: CLOSED 2026-10-20; portable frontier fixtures and explicit environment checks pass

The 2026-10-17 PowerShell full run completed: 3,565 passed, six failed, eight
skipped, 17 deselected, 99.96% coverage. All Vim checks passed. Remaining tests:

- test_state_user_command_durable_lineage_and_subsequent_inference
- test_state_turn_pending_tools_execute_at_frontier
- test_state_turn_run_command_parity
- test_state_intermediate_user_turn_edit_branches_dag
- test_explicit_user_shell_result_is_user_scoped_and_renderable
- test_first_successor_step_synchronizes_messages_after_continuation_parent

Most report WinError 2 from subprocess launch; one reports no callable frontier
consequences. Reproduce each before assigning a common cause. Git Bash supplies
executables that native PATH may lack, including a standalone echo executable.

Acceptance now completes all 17 scenarios, with 16 passes and one WinError 2
failure in the mixed multi-instance in_order scenario at direct echo execution.

Classify product gaps versus fixtures that assume POSIX executables. Preserve
direct executable argv, explicit shell-script runtime selection, model tool
authorization, and the separate direct-user-intent path; do not silently route
every missing executable through a shell. Verify source-order and lineage
contracts using actual portable commands, with native PATH and explicit runtimes.

## Resolution — 2026-10-20

Reproduced all six failures after the upstream merge (six failed, 85 passed).
They depended on standalone echo, printf, or cat. Replaced the executable
dependencies in lineage/projection/frontier tests with the current Python
interpreter, retaining real process execution and all ordering, branching,
durable-record, and projection assertions. Pending model tool tests grant only
that selected executable through the existing glob grant syntax. Successor
restoration uses the arbitrary-command lane rather than misrepresenting Python
as a cat-only file-restoration command. No production shell fallback changed.

The environments remain separate: six matrix cases explicitly set subprocess
PATH to System32 alone or Git MSYS usr/bin plus System32. Native cases verify
missing standalone utilities; MSYS cases execute real cat, printf, and echo.
No parent PATH mutation. Select them independently with pytest
`tests/test_shell_runtime_matrix.py -k native-windows` or `-k msys`.
The existing explicit Bash/WSL/PowerShell/pwsh cases remain intact.

Verification: 118 tests passed in 16.51 seconds across the three frontier
modules, runtime matrix, and all 17 acceptance scenarios. Matrix alone:
10 passed in 2.49 seconds. Repository-wide Ruff passes. Actual isolated CLI
run rendered a successful user-scoped shell result containing
`native-frontier-ok` in its inert stdout block. Remaining mypy journal-lock
errors and broad coverage gates belong to the master restoration task.
