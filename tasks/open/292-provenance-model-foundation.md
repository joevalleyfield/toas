## Goal

Establish message provenance as a first-class inline attribute on message events, wire the straightforward creation sources, and add `message_id` attribution to `llm_call` records.

## Why Now

Provenance is a creation-time fact. The sessions that will carry meaningful provenance don't exist yet — this task creates the conditions for them. See `docs/storage-notes.md` for the full design rationale.

## Scope

**Provenance attribute shape** (inline on message events):

```json
{"source": "llm_generated"}
{"source": "user_authored"}
{"source": "adopted"}
{"source": "user_correction", "corrects": "n11"}
```

`user_correction` is handled in `293`. This task covers the remaining three.

**`llm_generated`** — written by `cli.py` when `generate()` produces a node; the provenance attribute is attached to the returned node before `write_message_events` is called. No change to message event schema required; `provenance` is just a new optional field.

**`user_authored`** — default for user-role messages that arrive without provenance through normal transcript alignment. Written in `step()` when nodes from the transcript are materialized without an identified generation or adoption source.

**`adopted`** — written by the `/extract <n>` command handler when it emits a user node containing adopted assistant content.

**`llm_call` attribution** — add `message_id` to `llm_call` records, following the `tool_request` pattern. The message ID is known after `write_message_events` in `cli.py`; write an updated or follow-on `llm_call` record with the `message_id`, or restructure the write order so the ID is available. Choose the approach that least disrupts the existing write path.

## Backwards Compatibility

No migration, no backfill, no reconstruction from existing records. Old messages without a `provenance` field are handled gracefully — code reads provenance as optional, falls back to `None` or an unknown marker where needed. Degraded behavior is acceptable; crashes are not. A future transition strategy is a conscious choice, not a default obligation.

## Intended Inputs

- message write path in `cli.py` (`write_message_events`, `generate()`)
- `/extract` command handler in `step.py`
- `write_llm_call_record` in `graph.py`

## Intended Outputs

- `provenance` attribute on `llm_generated`, `user_authored`, and `adopted` message nodes
- `message_id` on `llm_call` records
- all read paths treat `provenance` as optional without crashing
- tests covering attribute presence on each source, `llm_call` attribution, and graceful handling of messages without provenance

## Non-Goals

- no `user_correction` source in this task (that is `293`)
- no index (`294`)
- no provenance surfacing in CLI inspection commands yet (that follows naturally once the data exists)
- no backfill of existing sessions
