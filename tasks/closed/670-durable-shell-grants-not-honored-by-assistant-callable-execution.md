# 670 Durable Shell Grants Not Honored By Assistant Callable Execution

Status: closed

## Objective
Ensure assistant callable shell execution honors durable `/shell` grant records from the event log.

## Problem
A recon transcript showed `/shell allow jj` producing a session grant record, but a later assistant-authored `operation: shell` with `argv: ["jj", ...]` was still evaluated against the default shell allow-list.

## Cause
The default assistant callable execution closure resolved shell grants from reconstructed message working state only. After task 512, `/shell` grants are operational records, so execution policy must include durable event-backed grant state.

## Scope
- Thread durable event records into assistant callable shell grant resolution.
- Preserve the same-turn boundary where transcript text such as `/shell allow jj` is inert until it has been executed and recorded.
- Add focused regression coverage for a durable prior grant enabling a later assistant shell call.

## Acceptance Criteria
- A previous `shell_scope_grant` event for `jj` allows a later assistant callable shell plan whose leading command is `jj`.
- Same-turn transcript-only grants remain unavailable to that assistant shell call.
- Targeted tests pass.

## Progress
- 2026-05-31: Opened from recon note `/Users/tim/Documents/Projects/toas-recon/.toas/recon-pass1.md`.
- 2026-05-31: Threaded durable event records through the default assistant callable execution dependency path and CLI step kwargs.
- 2026-05-31: Added regressions for durable grant execution, same-turn transcript grant inertness, CLI event threading, and helper signature coverage. Focused `uvt` verification passed.
- 2026-05-31: Full `./.codex-local/bin/uvt run pytest` reached functional green (`1760 passed, 1 skipped, 17 deselected, 1 xfailed`) but exited nonzero on coverage gates (`91.70% < 95%`, missing-files cap `34 > 13`).
- 2026-05-31: Closed after durable event-threading fix and regression coverage landed.
