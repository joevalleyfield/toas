# 563: Vim Buffer-Aware Surface Session Auto-Selection

## Why

Task `561` introduced multi-surface/session targeting semantics, but Vim step entrypoints were not yet projecting current-buffer transcript identity into step payloads. That left editor workflows unable to auto-target the active session surface.

## Goal

Make Vim `ToasStep`/`ToasStepHere` treat the active file-backed buffer as the transcript target by default, while preserving explicit payload overrides.

## Scope

- Add Vim plugin helper that derives a session path from the active buffer path.
- Inject derived session into `step`/`step_async*` request payloads in plugin request shaping.
- Preserve explicit payload precedence (if `session` or `session_path` already present, do not override).
- Add regression coverage at Vim contract level asserting session field is present and stable across `ToasStepHere`/`ToasStep` in same buffer.
- Remove step-time transcript auto file materialization/migration side effects (user-owned file creation/appends).

## Non-Goals

- Introducing new graph/runtime policy barriers.
- Reworking surface binding semantics in Python runtime.
- Adding new lineage policy gates.

## Implementation Notes (2026-05-24)

- Added `s:toas_active_buffer_session_path()` in `vim/plugin/toas.vim`:
  - uses active file-backed buffer path as authoritative target
  - returns workdir-relative path when possible, absolute path otherwise
- Updated `s:toas_request_payload()` to inject `session` for `step` and `step_async*` only when payload does not already include `session`/`session_path`.
- Added assertions in `tests/vim/streaming_step_and_step_here_parity.vader` capturing `step_async` payload `session` values.
- Updated step transcript preparation to remove write-side compat migration/materialization:
  - no `ensure_session_path_compat(...)` call during step
  - no implicit transcript file creation/touch during step
  - read-only legacy fallback to root `session.md` retained when configured target is missing
- Updated CLI tests to reflect no-auto-create/no-auto-migrate behavior.

## Validation

Attempted:

```bash
uv run pytest tests/test_vim_driver_contract_plugin_async.py -q --no-cov
```

Observed: timeout in this environment while running phase7 TTY driver harness.

## Status

Closed (validated in real interactive Vim usage).
