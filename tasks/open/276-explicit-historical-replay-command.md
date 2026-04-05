## Goal

Refactor `/extract` into a frontier adoption helper: preview candidate command content from the latest assistant message, then select one candidate to inline as user content for normal `step` execution.

## Why Now

`/extract` still carries execution-oriented semantics (`--dry-run`, `--execute`) that duplicate existing `step` behavior and provide little operator value. The useful workflow is: preview assistant-authored command options, adopt one inline, then let normal `step` execute it.

## Scope

- replace `/extract --dry-run|--execute` with:
  - `/extract` (no args): list candidates from latest assistant message with concrete previews
  - `/extract <n>`: emit selected candidate as a user message node for adoption
- candidate list should include concrete runnable content, not abstract summaries
- `/extract <n>` does not execute tools directly; it only stages user content
- normal `step` on subsequent turn performs execution using existing paths
- historical replay is explicitly out of scope for `/extract`; may be a future dedicated command

## Intended Inputs

- current frontier-scoped `/extract` behavior from `275`
- callable detection helpers for tool plans and loose command YAML
- existing step consequence model for emitting user nodes

## Intended Outputs

- `/extract` preview output with numbered concrete candidate content
- `/extract <n>` adoption path that appends a user node containing selected command content
- tests covering preview rendering, index selection, invalid index, and no-candidate failure

## Constraints

- no direct tool execution in `/extract` command handler
- no historical transcript scan in `/extract`
- durable history/message-lineage invariants unchanged

## Non-Goals

- no historical replay command in this task
- no LLM-assisted candidate ranking

## Done When

- `/extract` (no args) lists concrete candidates from latest assistant message
- `/extract <n>` emits selected candidate as user content and does not execute directly
- legacy flags (`--dry-run`, `--execute`, `--force`) are removed from `/extract`
- docs/tests reflect adoption-first semantics
