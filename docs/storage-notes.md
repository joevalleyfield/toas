# Storage Notes

Design intent, implementation drift, and access-pattern thinking for the TOAS event log.

---

## Original ID And Parent Design Intent

The original design intent for `events.jsonl` was sparse identity: message events in the common sequential case would carry no `id` or `parent` fields. Position in the file — line index among message events — would be the implicit identity, and the implicit parent would always be the previous message event. Explicit `id` and `parent` would only appear at deviation points: branch starts, joins, or any event that could not be inferred from position alone.

This keeps the common case compact. A linear session is a flat list of role/content pairs with no graph bookkeeping overhead. The graph topology only materializes in the record when it actually deviates from the linear default.

`vision.md` preserves a trace of this: "Default `id` sequencing, when elided, is also over message events only." That line was meant to describe a live behavior, not a hypothetical.

---

## Current Drift

Early implementation — prior to the current codebase — wrote explicit `id` and `parent` on every message event. That schema is correct and semantically equivalent to the sparse design; it is simply the verbose version. The graph topology is fully recoverable in either case.

The drift is not a showstopper. The explicit-ID-on-every-record schema is what the current code reads and writes, and changing it now would require a migration. It is documented here so the original design intent is not lost and so future optimization work has context.

---

## Index Design

Because JSONL lines are variable in length, an index over the event log cannot be position-based without a secondary structure. The intended design:

- A companion index file (e.g., `events.idx`) with fixed-size records
- Each record covers one message event: `(line_number, byte_offset)` at minimum, possibly `(line_number, byte_offset, message_id)` for direct lookup by ID without scanning
- Fixed-size fields make the index seekable: given a message index `n`, seek to `n * record_size` and read directly
- The index is append-only and written in sync with the event log; it is a derivative artifact, not a source of truth

With this index:
- Sequential access by position is O(1)
- Lookup by message ID requires a linear scan of the index (not the full event log) or a separate hash index
- Ancestry walks over the full log remain O(depth) but the per-hop cost drops from a full-file scan to an index seek

The index is not yet implemented. The current ancestry walk in `_lineage()` in `graph.py` scans the full message event list on every call. For sessions of current scale this is acceptable. As sessions grow longer, or as provenance queries become common, the index is the right path to O(1) access without denormalizing content.

---

## Provenance Design Intent

Provenance is a fact at message creation time. It answers "how did this content come to exist" — a question orthogonal to lineage ("what is this a response to").

**Design:**

- Provenance lives as inline attributes on message records, not as a separate record type
- Messages are the primary record type; provenance enriches them at write time
- No retroactive assignment; messages created before provenance was introduced simply lack the attribute

**Sources (initial set):**

- `user_authored` — user typed this directly
- `llm_generated` — produced by a model call
- `user_correction` — user edited an LLM-generated message; carries a `corrects` pointer to the message being replaced
- `adopted` — content staged via `/extract <n>` from an assistant message into a user turn

**Correction records** carry a `corrects` field pointing to the message ID that was deemed insufficient. The corrected message still exists in the event log (branching, not mutation). The pair — original generation plus correction — is the preference signal. It is self-contained in the graph: the `corrects` pointer reaches the original, and the original's lineage reaches its `llm_call` record.

**`llm_call` attribution:**

`llm_call` records should carry a `message_id` field referencing the message event they produced, following the same pattern as `tool_request`. This lets the graph walk in either direction: message → find its `llm_call` by scanning for `llm_call` records with matching `message_id`; `llm_call` → find the message directly. No content is duplicated; the message is the content store.

**Why inline rather than a separate provenance record type:**

A separate record type would require joining across record kinds to reconstruct provenance for a message. Inline attributes keep the message self-describing at the cost of slightly larger per-record size. Given that provenance is a creation-time fact with a fixed small shape, the inline cost is low and the join cost is avoided.

---

## Access Patterns That Want An Index

Once provenance is in place, the following queries become common:

- Find all user corrections in a session (messages with `provenance.source = user_correction`)
- Find the `llm_call` for a given message (scan `llm_call` records for `message_id = n7`)
- Walk the correction chain: given a correction, find what it corrects, and what that corrects, recursively
- Find all messages produced by a specific model or call configuration

These are all O(n) over the raw event log today. The byte-offset index makes them O(1) for direct access and O(k) for scans where k is the number of matching records rather than the total log size.

The index is the right answer to performance concerns here, not denormalization of content into secondary records.
