# 564: Vim Workdir Resolution Without `toas session-path` Shellout

## Why

Vim plugin currently shells out to `toas session-path` during workdir resolution. Now that step payloads already carry active-buffer `session` identity, this subprocess dependency is unnecessary and adds avoidable latency/churn.

## Goal

Remove Vim plugin dependency on `toas session-path` shelling for workdir resolution while preserving stable local-host/RPC behavior.

## Scope

- Refactor `s:toas_workdir()` to avoid calling `toas session-path`.
- Use editor-local signals first:
  - `g:toas_workdir` when set
  - active buffer path and/or current working directory
  - upward probe for repo root markers (`.toas`, `toas.toml`)
- Preserve cross-platform path normalization behavior.
- Keep request payload session targeting behavior unchanged.

## Non-Goals

- Runtime/session precedence changes in Python.
- Host protocol changes.

## Status

- [x] Completed
- [x] `s:toas_workdir()` refactored in `vim/plugin/toas.vim`.
- [x] Shellout to `toas session-path` removed.
