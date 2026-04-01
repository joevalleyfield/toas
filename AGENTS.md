# TOAS Agent Notes

## Purpose

TOAS is a transcript-oriented operator over an append-only event log.

The important split is:
- `session.md` is the user-controlled working proposal
- `events.jsonl` is durable history
- `toas step` accepts transcript state, synchronizes it into history, and resolves one layer of consequence

The system is not a hidden loop.

## Current Model

### Message events

Message events are graph-native history entries with:
- `id`
- `parent`
- `role`
- `content`
- `metadata`

They live in message-event space only.

Default `id`/`parent` behavior is defined over message events, not all log records.
Control records and tool records do not participate in message-event numbering.

### Control records

Non-message operator state is stored in `events.jsonl` as records such as:
- `jump`
- `anchor`

`jump` is no longer stored in `jump.txt`.

### Tool records

Tool activity is not a message type.

Callable message events can produce:
- `tool_request` records
- `tool_result` records

`RESULT` blocks are stdout serialization for forward append convenience, not transcript authority.

## Key Invariants

- Never rewrite `session.md` from the system side.
- Never mutate prior history entries.
- Editing prior transcript-aligned content means branching, not undoing acceptance.
- Continuation from a non-tip lineage must use explicit parentage.
- Adjacent user message events are concatenated only at LLM-input projection time, not in storage.

## Important Files

- [docs/vision.md](/Users/tim/Documents/Projects/toas/docs/vision.md): canonical design notes
- [src/toas/cli.py](/Users/tim/Documents/Projects/toas/src/toas/cli.py): `step` / `jump` entrypoints
- [src/toas/graph.py](/Users/tim/Documents/Projects/toas/src/toas/graph.py): history I/O, projections, control/tool record helpers
- [src/toas/step.py](/Users/tim/Documents/Projects/toas/src/toas/step.py): transcript alignment and one-step consequence resolution
- [src/toas/transcript.py](/Users/tim/Documents/Projects/toas/src/toas/transcript.py): transcript parsing
- [tests](/Users/tim/Documents/Projects/toas/tests): executable contract

## Behavior To Preserve

### `step`

- Reads transcript proposal
- Aligns against message-view history
- Appends only new consequences
- Emits only stdout frontier blocks

### `jump`

- Appends a durable `jump` control record
- Active bind index is derived from history, using the latest jump record

### Projection

- `project_transcript(...)` rebuilds a usable lineage-backed transcript view
- `project_llm_input(...)` concatenates adjacent user events
- Neither projection claims authority over the exact user-edited `session.md`

## Implementation Bias

When extending the system:
- prefer new durable records over sidecar state
- keep message events, control records, and tool records distinct
- put serialization/projection rules at the boundary, not in storage
- keep the CLI thin and move semantics into `graph.py` / `step.py`

## Verification

Run:

```bash
uv run pytest
```

The tests are the quickest way to confirm the current contract before changing behavior.
