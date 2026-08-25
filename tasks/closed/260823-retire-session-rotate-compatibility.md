Filed as: 260823-retire-session-rotate-compatibility
FKA:
AKA: continuation naming cleanup; rotate alias retirement
Legacy index:

keywords: runtime, vim, cli, protocol, continuation, compatibility, cleanup

Related: `260803-session-rotation-lifecycle`; `260804-successor-continuation-remediation`

# Retire Session-Rotate Compatibility Names

## Objective

Make successor continuation the only active user-facing and callable
terminology. Retain the established `<leader>r` shortcut, which already calls
the canonical `:ToasContinue`, but remove the obsolete `rotate` command,
request, facade, and runtime aliases.

## Acceptance Criteria

- [x] `:ToasContinue`, `session_continue`, and `run_session_continue` are the
  only active continuation surfaces; `<leader>r` remains unchanged.
- [x] `:ToasRotate`, `session_rotate`, `run_session_rotate`, and
  `rotate_session` are no longer callable.
- [x] Active documentation and help use continuation/successor terminology;
  historical closed-task and release records may retain their original names.
- [x] Tests cover the canonical surfaces and prove the retired names are absent.
- [x] Focused tests pass and the full-suite result is recorded.

## Completion Evidence

Completed 2026-08-23. The compatibility aliases and `:ToasRotate` command were
removed; `<leader>r` continues to invoke `:ToasContinue`. Active documentation,
request dispatch, facades, and tests now use continuation terminology. Historical
closed-task and release notes retain prior names only as archival evidence.

Focused continuation/request and source-surface checks: 77 passed.
Full suite: 2,853 passed, 20 sandbox-only socket/Vim environment failures, and
9 deselected, with 100% coverage.
