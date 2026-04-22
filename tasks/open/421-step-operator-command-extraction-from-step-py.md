## Goal

Extract the monolithic operator-command dispatcher from `src/toas/step.py` into a focused runtime module boundary.

## Why Now

`code_survey` identifies `_execute_operator_command` in `step.py` as the largest function in the repository (`786` lines), making targeted edits high-risk and slowing small-model execution reliability.

## Scope

- move `_execute_operator_command` logic into `src/toas/runtime/operator_commands.py`
- split major command families into focused helpers (`/prompt`, `/config`, `/shell`, `/extract`, `/replay`, control/meta)
- keep `step.py` compatibility wrapper and call shape stable during migration
- add focused tests for moved command handlers and error branches

## Intended Behavior

- operator command handling remains behavior-identical while becoming locally testable in smaller units
- `step.py` sheds the largest dispatch block and becomes orchestration-first

## Constraints

- no semantic drift in transcript synchronization, durable record writes, or tool execution side effects
- preserve direct-user-shell vs model-callable-tool boundary semantics
- land in small commits (one command family cluster at a time)

## Done When

- `_execute_operator_command` no longer owns the full command family logic in `step.py`
- moved operator-command module has direct tests for success and failure branches
- full `uv run pytest` passes
