# 336: Windows daemon detachment parity for `toas daemon start`

## Summary
Harden daemon process launch behavior on Windows so it more closely matches current POSIX detachment semantics.

## Problem
Current launch behavior already uses `stdin/stdout/stderr=DEVNULL` and `start_new_session=True`, which is strong on POSIX. On Windows, this is only partial detachment and may still couple process lifecycle/console behavior more than intended.

## Goals
- Keep current POSIX behavior unchanged.
- Improve Windows detachment reliability for daemon lifecycle commands.
- Preserve current CLI/Vim UX contracts (`toas daemon start`, `:ToasStep`, async watch/cancel).

## Proposed Direction
- In daemon startup path, add Windows-specific `creationflags` when `os.name == "nt"`:
  - `DETACHED_PROCESS`
  - `CREATE_NEW_PROCESS_GROUP`
  - optionally `CREATE_NO_WINDOW` (validate whether needed)
- Continue routing stdio to `DEVNULL`.
- Keep `start_new_session=True` for non-Windows and validate compatibility behavior on Windows.
- Ensure no regression in pid/status detection and stop semantics.

## Acceptance Criteria
- On POSIX, behavior is unchanged.
- On Windows, daemon starts without terminal coupling and survives parent-command completion in expected dev workflows.
- `toas daemon status` and `toas daemon stop` continue to work for started processes.
- Tests cover launch argument construction per platform branch.

## Notes
- This is hardening, not a blocker for current POSIX-centric workflows.
- If `CREATE_NO_WINDOW` causes edge-case issues, keep it optional or configurable.
