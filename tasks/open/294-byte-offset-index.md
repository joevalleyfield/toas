## Goal

Build a fixed-size seekable companion index to `events.jsonl` that enables O(1) message access by position and cheap ancestry walks without scanning the full event log.

## Why Now

Once provenance (`292`, `293`) is in place, queries over message events become common: find all corrections, walk correction chains, find the `llm_call` for a given message. Today those are all O(n) over the raw event log. The index makes them O(1) for direct access. It also pays off for ancestry inspection (`295`) and divergence summary (`296`), where per-hop cost currently requires a full-file scan.

## Scope

**Index file** — a companion file (e.g., `events.idx`) written alongside `events.jsonl` in the session directory. Contains one fixed-size record per message event.

**Record shape** (per message):

```
| line_number (4 bytes) | byte_offset (8 bytes) | message_id (variable, padded to fixed width) |
```

Exact field widths TBD at implementation; the constraint is that each record is the same size so `record_n` is at `n * record_size`.

**Write path** — index is appended in sync with `write_message_events` in `graph.py`. One record per message event written.

**Read path** — given message index `n`, seek to `n * record_size` and read directly. Given message ID, linear scan of index (not full event log). For the current session scale, linear index scan is acceptable; a hash layer is a future optimization.

**Recovery** — index is a derivative artifact. If absent or truncated (e.g., process killed mid-write), it can be rebuilt from `events.jsonl`. A `toas index rebuild` command or equivalent should be available for manual recovery, but normal operation should not require it.

**Backwards compatibility** — sessions without an index file continue to work; all access paths fall back to full event log scan when the index is absent. No migration required.

## Intended Inputs

- `write_message_events` in `graph.py`
- session directory path resolution (existing pattern)

## Intended Outputs

- `events.idx` written and appended in sync with message events
- O(1) seek by message position
- linear scan of index (not full log) for ID lookup
- rebuild command for recovery
- fallback to full scan when index absent
- tests covering: index written on message write, seek by position, ID scan, absent-index fallback, rebuild from log

## Non-Goals

- no hash index (secondary structure for O(1) ID lookup)
- no coverage of non-message event types
- no index over `llm_call` or `tool_request` records
- no compaction of the index file (append-only matches the event log)
