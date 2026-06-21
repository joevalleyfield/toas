# Enable Shell Globbing

## Problem
Shell commands with glob patterns (e.g., `$ cat tasks/open/566-*`) do not expand wildcards. The current shell execution path likely invokes binaries directly or lacks a shell wrapper to handle metacharacters.

## Goal
Ensure that shell commands executed via the `$ ...` user-intent shorthand and the `shell` tool support standard shell globbing.

## Context
- The `shell` tool uses a bounded list of allowed binaries (`awk, cat, echo, find, head, ls, pwd, rg, sed, tail, wc`).
- The `$ ...` shorthand is executed through a separate user-intent path but records `tool_request` / `tool_result` using the `shell` shape.
- Glob expansion is a shell feature, not a binary feature.

## Scope
- `src/toas/step.py`: Check how the `$ ...` user-intent path is handled.
- `src/toas/runtime/` or `src/toas/tools.py`: Check how the `shell` tool executor invokes commands.

## Implementation Bias
- If the current path uses `subprocess` with `argv`, switching to `sh -c` or `bash -c` may resolve globbing immediately.
- Verify that glob expansion does not break security constraints (e.g., path traversal).

## Verification
- Run `$ cat tasks/open/240522*` and confirm it reads the task file.
- Run `shell` tool with globs and confirm expansion.

## Progress

- [x] Modified `needs_shell` in `src/toas/tools_cluster/shell_ops.py` to detect glob characters (`*`, `?`, `[`, `]`).
- [x] Added unit test coverage for glob-triggered shell routing in `tests/test_tools_shell_ops.py`.
- [x] Confirmed unit tests pass (noting 2 pre-existing coverage gaps in unrelated files).
- [x] Verified end-to-end behavior in session transcript.
- [x] Closed task.

