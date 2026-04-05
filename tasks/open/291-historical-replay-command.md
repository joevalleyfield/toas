## Goal

Implement a dedicated command for replaying a historical callable message from transcript history — the use case that `/extract` explicitly shed during the 275/276 adoption pivot.

## Why Now

`/extract` (post-276) is scoped to the latest assistant message and stages content for adoption rather than executing directly. The historical replay use case — find a callable message from earlier in the session, re-run it now with current context — was explicitly deferred as "may be a future dedicated command." This task is that command.

## Background

Task `271` originally described this as part of `/extract`. The adoption model proved cleaner for the primary operator workflow. Historical replay is a distinct enough operation (different target scope, different execution semantics, different failure modes) that it warrants its own command rather than flag proliferation on `/extract`.

## Scope

- `/replay [--dry-run] [--index <n>]`
  - without `--index`: scan working history for callable messages, report candidates; if exactly one, confirm intent before executing
  - with `--index <n>`: target the nth candidate directly
  - `--dry-run`: show what would execute without executing
- candidate detection reuses the same extraction logic as `/extract` but scans all non-frontier messages rather than just the latest assistant turn
- execution writes `tool_request`/`tool_result` records referencing the original message ID
- guard: refuse to re-execute a message that already has associated `tool_request` records; require `--force` to override
- execution uses current command context (cwd, workspace), not reconstructed historical context — this is explicit and surfaced in the dry-run output

## Intended Inputs

- callable candidate detection from `step.py`
- `write_tool_request_record`, `write_tool_result_record` in `graph.py`
- message lineage from `graph.py` (to identify which messages already have tool records)
- `OperatorConfig` for workspace/cwd context

## Intended Outputs

- `/replay` command with dry-run, index selection, and already-executed guard
- `command_request`/`command_result` records on execution
- tests covering: candidate listing, index selection, dry-run, already-executed rejection, `--force` override, no-candidate failure

## Constraints

- does not modify any message content or create new message events — tool records only
- execution context is current, not historical; dry-run must make this explicit
- `/extract` behavior must remain unchanged by this work

## Non-Goals

- no context reconstruction (using historical cwd/workspace at time of original message)
- no LLM-assisted candidate ranking or selection
- no chaining of replay results into subsequent turns automatically
