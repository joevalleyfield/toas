Filed as: 261030-multi-grant-shell-syntax
FKA:
AKA: multi-grant shell syntax; /shell allow multiple commands; batch shell grants
Legacy index:

keywords: runtime, shell, grants, syntax, ergonomics, rotation, policy

Parent:
Depends on: `261029-serialize-grants-on-session-rotation`
Blocks:
Blocked by:
Related: `260830-exec-grant-policy-matchers`

# Multi-Grant Shell Syntax and Compact Serialization

Support granting or revoking multiple commands in a single `/shell [add|allow|remove|deny|unset]`
invocation, and serialize successor session continuation grants compactly.

## Current Reality

1. `/shell allow` and `/shell add` (and `remove`/`deny`/`unset`) only accept a single
   grant argument:
   `_parse_scope` in `src/toas/runtime/operator_command_prompt_workspace.py` requires
   `len(args) == 2` or `len(args) == 4` with `--scope`.
   Typing `/shell allow jj pytest uv` raises a usage `ValueError`.
2. `parse_transcript_shell_grant_events` in `src/toas/runtime/policy.py` similarly
   only inspects `args[1]`.
3. When rotating or continuing a session via `session continue`, `_render_successor_replay`
   in `src/toas/runtime/session_rotation.py` emits a separate line for each granted
   or removed command:
   ```markdown
   ## TOAS:CONTROL
   /shell add cmd1
   /shell add cmd2
   /shell add cmd3
   ```
4. This adds unnecessary vertical clutter to transcripts and requires repetitive
   command invocations when allowing multiple tools in a session.

## Desired Reality

1. Both the interactive operator command and transcript parser accept one or more grants:
   ```text
   /shell allow jj pytest uv
   /shell add git jj uv --scope workspace
   /shell remove cat sed
   ```
2. Any flag starting with `--` is validated against `--scope <scope>` at the end of the arguments.
3. Operator command execution updates each grant in durable `events.jsonl` via `_apply_shell_scope_updates()`,
   recording a `shell_scope_grant` event for each specified grant.
4. The result confirmation message cleanly summarizes the action:
   - For single grant: `shell grant updated: add jj (scope=session)`
   - For multiple grants: `shell grants updated: add jj pytest uv (scope=session)`
5. Session rotation serializes multiple added/removed grants compactly onto single lines:
   ```markdown
   ## TOAS:CONTROL
   /shell add jj pytest uv
   ```
6. Full test suite passes with 100.00% statement coverage via `./scripts/check.sh`.

## Acceptance Criteria

- [x] `/shell allow <cmd1> <cmd2> ...` succeeds interactively and adds all commands to the effective shell allowed list.
- [x] `/shell allow <cmd1> <cmd2> ... --scope <scope>` sets the specified scope for all listed commands.
- [x] `/shell [remove|deny|unset] <cmd1> <cmd2> ...` revokes all listed commands.
- [x] Transcript parser `parse_transcript_shell_grant_events()` emits events for all commands listed on a multi-grant line.
- [x] `_apply_shell_scope_updates()` writes durable `shell_scope_grant` records for all grants in a multi-grant update.
- [x] Session continuation serializes multiple custom grants into compact single-line `/shell add ...` and `/shell remove ...` directives.
- [x] Tests cover multi-grant addition, removal, scoping, error cases, and compact continuation serialization with 100.00% statement coverage.

## Verification Evidence

1. Updated `_parse_grants_and_scope` and `_shell_runtime_mutation_result` in `src/toas/runtime/operator_command_prompt_workspace.py` to accept multiple grant arguments with optional trailing `--scope <scope>`.
2. Updated `_apply_shell_scope_updates` in `src/toas/runtime/session_step_edges.py` to persist durable records for each grant in `grants`.
3. Updated `parse_transcript_shell_grant_events` in `src/toas/runtime/policy.py` to extract all tokens from multi-grant lines in `session.md` and emit corresponding `shell_scope_grant` events.
4. Updated `session_rotation.py` to serialize multiple added/removed grants compactly as single-line `/shell add cmd1 cmd2 ...` and deduplicate across replay nodes by grant identity.
5. Unit and integration tests added in `tests/test_runtime_operator_command_handlers.py`, `tests/test_runtime_session_step_edges.py`, `tests/test_runtime_policy.py`, and `tests/test_runtime_session_rotation.py`.
6. Full test suite `./scripts/check.sh` passed cleanly with 100.00% statement coverage (3618 passed, 0 missed statements across 23140 stmts), ruff clean, and mypy clean.
7. Conducted operator perspective verification: verified end-to-end interactive single-grant and multi-grant execution, scoping, confirmation messages, and payload shapes.
