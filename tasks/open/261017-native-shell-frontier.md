# Native Windows Shell Frontier Verification

Filed as: 261017-native-shell-frontier
FKA:
AKA: Windows echo launch; direct argv portability; shell frontier parity
Legacy index:

keywords: runtime, hardening, compatibility, windows, shell, frontier

Parent: `261015-windows-compatibility-restoration`
Related: `261015-selectable-shell-runtime`; `261015-shell-launcher-reader-portability`

Status: OPEN; classify six native-suite failures and one acceptance failure

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
