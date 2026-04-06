## Goal

Detect at step time when a user-edited message replaces an LLM-generated one, and record `provenance.source = user_correction` with a `corrects` pointer to the original message ID.

## Why Now

Correction capture is a creation-time fact. The moment a corrected message is materialized in the graph, the intent is knowable. After that point, the append-only structure and the creation-time provenance model make retroactive detection impossible without violating design constraints. This task depends on `292` landing first: the `llm_generated` provenance attribute on the original message is what the correction detection logic reads to decide whether a node was replaced by user action.

## Scope

**Detection logic** — in `step()`, during transcript alignment: when a new user-role node is materialized that occupies the same position as a node that previously existed with `provenance.source = llm_generated`, treat the incoming node as a correction. Attach `provenance = {"source": "user_correction", "corrects": "<original_message_id>"}` before calling `write_message_events`.

**Heuristic fallback** — messages written before `292` landed will lack a `provenance` field. For pre-provenance messages, correct detection cannot be confirmed. Do not guess; leave `provenance` absent rather than misattribute. Degraded behavior (no correction pointer on pre-provenance messages) is acceptable; false correction attribution is not.

**Provenance attribute shape**:

```json
{"source": "user_correction", "corrects": "n11"}
```

The `corrects` value is the message ID of the original LLM-generated message being replaced. The original message is not deleted or modified — it remains in the event log as a branch point.

## Intended Inputs

- transcript alignment loop in `step.py`
- `provenance` field on existing message nodes (written by `292`)
- message ID resolution from `graph.py`

## Intended Outputs

- `provenance.source = user_correction` with `corrects` pointer on replacement nodes
- heuristic fallback: no provenance on nodes that replaced pre-provenance messages
- all read paths treat `provenance` as optional without crashing (established in `292`)
- tests covering: correction detected correctly, `corrects` pointer points to original ID, no false attribution on pre-provenance messages, original message still present in graph after correction

## Non-Goals

- no retroactive detection of corrections from existing sessions
- no LLM-assisted correction quality scoring
- no UI surfacing of correction pairs (that follows in `295`/`296`)
- no `user_correction` handling in provenance reads beyond the shape established in `292`
