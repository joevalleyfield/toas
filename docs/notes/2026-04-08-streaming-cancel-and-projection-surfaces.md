# Streaming, Cancellation, and Projection Surfaces

## Insight

Streaming should be treated as transient transport, while canonical history remains append-only durable records. Projection can be read-only even when the surface it projects into is a writable control surface.

## Why It Matters

This keeps TOAS semantics stable while enabling responsive operator workflows (especially in Vim) and multi-client control without hidden mutation or ontology drift.

## Implications

- `run_id` should be first-class for start/watch/cancel control-plane actions.
- Blocking step semantics should be complemented by async run semantics.
- Stream output should be live and ephemeral; durable history should only record finalized outcomes.
- Multiple simultaneous projections of `events.jsonl` are viable as long as they remain reversible to canonical event IDs.
- Writable behavior belongs to the interaction surface, not to mutation of projected historical records.

## Language Direction

- `projection`: read-only mapping of canonical history
- `surface`: writable operator control context attached to a projection
- `action`: operator input that appends new canonical events

## Near-Term UX Direction

- Vim should get explicit control-plane cancel (not just signal-kill behavior).
- Avoid committing to quickfix/work-queue semantics until there is demonstrated need.
- Prioritize a current-run stream panel + explicit terminal summary first.

## Open Questions

- Should async run be opt-in (`--async`) initially or runtime-default in daemon mode?
- Which transport events need strict ordering guarantees across mixed LLM/tool emissions?
- How much run metadata should be projected into transcript-facing views by default?
