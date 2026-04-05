## Goal

Implement a `/outline` command that produces a numbered structural summary of the current transcript — what was discussed and done, in sequence — without modifying any state.

## Why Now

Long sessions become hard to navigate. Before compacting or extracting, the operator needs a way to see the shape of the conversation and identify what's worth keeping, what's already done, and where to cut. `/outline` is a pure-read affordance that fills this gap.

## Scope

- `/outline` with no required arguments
- output: a numbered list, one entry per meaningful turn pair (user prompt + assistant response summary), with:
  - turn index
  - role of the initiating message
  - first line or brief summary of the content (truncated to ~80 chars)
  - whether the turn produced tool calls / shell commands / operator commands (annotated inline)
- optional `--head <head_id>` to outline a specific lineage rather than the active head
- purely informational: no writes to `session.md` or `events.jsonl`
- output is printed to result block; operator can use it to inform subsequent `/extract`, `/compact`, or manual editing decisions

## Design Notes

The outline does not require LLM assistance — it is derived mechanically from the projected message list:
- summarize by truncating the first non-empty line of each message content
- annotate callable messages using the same detection logic as `/extract --dry-run`
- no interpretation, ranking, or semantic grouping in this first pass

If the operator wants richer outlining (topic clustering, semantic labels), that is explicitly a follow-on and should be LLM-backed and config-gated.

## Intended Inputs

- projected message list from `message_view` / `project_transcript`
- callable message detection from `/extract` scan logic
- operator-command record model

## Intended Outputs

- `/outline` command producing a numbered turn summary
- `command_request`/`command_result` records written on execution
- tests covering basic outline output, callable annotation, `--head` targeting, and empty transcript edge case

## Constraints

- no writes to history or transcript
- must work on any head, not just the active one
- no LLM calls in this pass

## Non-Goals

- no semantic topic grouping or clustering
- no automatic selection of "interesting" turns
- no integration with `/compact` target selection (that's a follow-on)
