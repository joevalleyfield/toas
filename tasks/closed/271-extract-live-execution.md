## Superseded By

`275`, `276` — the execution-oriented model (direct tool dispatch with `--dry-run`/`--execute` flags and mid-history `tool_request`/`tool_result` attribution) was replaced by a content-adoption model: `/extract` previews callable candidates from the latest assistant message and stages the selected one as a user node for normal `step` execution. Historical replay remains a future dedicated command.

## Goal

Promote `/extract` from dry-run identification to live execution: actually run the identified callable message, write durable tool records, and produce output the operator can use.

## Why Now

Dry-run is useful for inspection but the operator still has to manually replay the identified action. Live execution closes the loop and makes extraction a complete mechanical workflow.

## Scope

- extend `/extract` to accept an `--execute` flag (alongside existing `--dry-run`)
- on `--execute`, resolve the target (same disambiguation logic as `--dry-run`), execute the plan or shell command, and write durable records:
  - `tool_request` referencing the original message ID
  - `tool_result` for each execution result
- refuse to execute a message that already has associated `tool_request` records — require explicit `--force` to override
- emit a result block describing what was executed and what records were written
- `--dry-run` and `--execute` are mutually exclusive; both absent is an error

## Intended Inputs

- `/extract --dry-run` from `234`
- `_extract_plan`, `_extract_user_shell_command`, `_extract_loose_command` in `step.py`
- tool execution path from `tools.py`
- `write_tool_request_record`, `write_tool_result_record` in `graph.py`

## Intended Outputs

- updated `/extract` command with `--execute` flag
- guard against double-execution with clear error message
- durable `tool_request`/`tool_result` records referencing the original message
- tests covering:
  - successful execution of a tool plan
  - successful execution of a user shell command
  - rejection when tool records already exist
  - `--force` override of rejection
  - mutual exclusion of `--dry-run` and `--execute`
  - index disambiguation path in execute mode

## Constraints

- execution uses the current command context (cwd, workspace) at the time `/extract --execute` is run, not reconstructed historical context
- no new message events are written — only tool records; the extraction result is surfaced as a `command_result` block
- `--dry-run` behavior must remain unchanged

## Non-Goals

- no automatic chaining of extracted results into subsequent turns
- no LLM-assisted extraction target selection
