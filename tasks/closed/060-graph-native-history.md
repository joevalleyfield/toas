## Goal

Promote `events.jsonl` from a linear append log into graph-native durable history for accepted message events.

## Scope

- Define durable entry shapes for accepted message events
- Introduce explicit identity and parent references
- Preserve append-only behavior while allowing multiple descendants
- Update log helpers to read and append graph entries

## Shape

Message event:
- id: str
- parent: optional[str]
- role: str
- content: str
- metadata: dict

## Rules

- History remains append-only
- Transcript blocks that enter history become message events
- Parent references define message lineage
- Default `id` and `parent` conventions are defined in message-event space only
- Non-message records do not participate in default message-event numbering or parentage
- Multiple children of the same parent are allowed
- Editing prior transcript-aligned content creates new lineage rather than mutating prior history
- Appending new transcript content without changing prior aligned content is continuation, not branching

## Non-Goals

- No full branch selection UX yet
- No replay optimization yet
- No tool request/result records yet

## Done When

- Message history is no longer dependent on physical line number for identity
- A new message event can explicitly continue an earlier message event
- Rewriting accepted transcript content can be expressed as a branch without mutating prior entries
