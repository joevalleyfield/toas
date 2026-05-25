# 565: Vim `ToasHostPid` Command

## Why

During local-host debugging it is useful to inspect the live TOAS host process PID directly from Vim. A previous attempt was not yet correct and was removed from `564` scope.

## Goal

Add a reliable `:ToasHostPid` command in `vim/plugin/toas.vim` that reports the current host PID when available, and `-1` when unavailable.

## Scope

- Add a helper to resolve PID from current host job handle.
- Prefer `job_info(...).process` / `job_info(...).pid` when available.
- Keep safe fallback behavior and return `-1` on unknown/unavailable state.
- Add user command surface: `:ToasHostPid`.

## Non-Goals

- Host lifecycle behavior changes.
- Additional runtime protocol/API fields.
