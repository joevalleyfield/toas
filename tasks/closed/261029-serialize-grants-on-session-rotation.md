Filed as: 261029-serialize-grants-on-session-rotation
FKA:
AKA: serialize grants on rotation; session continuation grants; carry forward shell grants
Legacy index:

keywords: runtime, session, rotation, grants, shell, continuation, closed

# Serialize Active Grants on Session Rotation

When rotating/continuing a session, serialize custom active shell grants from the
predecessor session directly into the successor transcript as an explicit control turn.

## Current Reality

When continuing a session via `session continue` (or `:ToasContinue` / `<leader>r`):
- `continue_session` in `src/toas/runtime/session_rotation.py` constructs a successor
  transcript containing the seed prompt, the compaction handoff, and any staged restoration commands.
- Predecessor transcript turns prior to `/compact` are discarded from the successor file.
- Any custom shell grants added in the predecessor (via `/shell add <cmd>`, `/shell allow <cmd>`,
  or control turns) are not carried forward into the successor transcript.
- When the successor transcript is stepped or rewritten, `_branch_shell_grant_events` only inspects
  the successor transcript buffer. Because the predecessor turns were discarded, custom grants are
  lost and commands like `pytest` fail with `[ERROR] shell: tool shell disallows command: ...`.

## Desired Reality

- When `continue_session` constructs the successor transcript, it evaluates the active shell grants
  in the predecessor context (combining predecessor transcript declarations and durable event grants).
- Any custom grants added beyond the baseline configured commands (`effective - configured`) are
  serialized into the successor transcript as an explicit `## TOAS:CONTROL` turn containing
  `/shell add <grant>`.
- Any baseline grants explicitly removed in the predecessor (`configured - effective`) are
  serialized as `/shell remove <grant>`.
- The control turn is placed in the successor transcript after the handoff and before any staged
  restoration commands, making active grants immediately visible and editable in the buffer.
- If no custom grants were added or removed in the predecessor, no extra control turn is generated.
- Both `/shell add` and `/shell allow` (and `/shell remove` / `/shell deny`) remain accepted
  inputs, while the serializer emits the canonical `/shell add` and `/shell remove` syntax.
- Downstream steps and rewrites in the continued session preserve the custom grants.

## Gap Analysis

- `session_rotation.py` does not resolve predecessor active grants against configured baseline.
- `_render_successor_replay` in `session_rotation.py` does not stage a control turn for active grants.
- Tests in `test_runtime_session_rotation.py` verify replaying graph nodes and restoration commands,
  but do not verify carrying forward custom grants.

## Acceptance Criteria

- `continue_session` detects custom grants active in the predecessor session.
- Successor transcript contains a `## TOAS:CONTROL` turn with `/shell add <grant>` for custom grants.
- Successor transcript steps cleanly without disallowing the granted commands.
- Baseline defaults without custom additions produce no extra control turn.
- 100.00% statement test coverage maintained across changed modules.

## Verification Evidence

- Added unit, integration, and end-to-end tests in `tests/test_runtime_session_rotation.py` and `tests/test_runtime_policy.py`.
- Verified targeted coverage: 100.00% statement coverage on `toas.runtime.policy`, `toas.runtime.step_runtime`, and `toas.runtime.session_rotation`.
- Ran full repository test suite: 3,609 passed, 9 skipped, 17 deselected at 100.00% total statement coverage.
- Ran `./scripts/check.sh` end-to-end: unit tests, acceptance tests, ruff, and mypy all passed cleanly.
- Conducted operator-perspective verification: inspected concrete transcript output rendered by `continue_session` showing `## TOAS:CONTROL\n/shell add ...` placed cleanly between the handoff and restoration commands.

