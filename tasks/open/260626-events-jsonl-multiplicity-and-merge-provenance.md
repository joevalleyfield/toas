Filed as: 260626-events-jsonl-multiplicity-and-merge-provenance
FKA:
AKA: events.jsonl multiplicity; lcp primacy; rebound provenance; mergeable journals
Legacy index:

keywords: docs, exploration, inception, research, graph, transcript, projection, boundaries, provenance

Parent: `260614-architecture-follow-through-coordination`
Related: `260626-transcript-parallelism-design-pressures`; `260509-multi-operator-orchestration`

# Events.jsonl Multiplicity And Merge Provenance

## Current Reality

TOAS already uses append-only `events.jsonl` durability plus LCP-based
transcript reconciliation. That gives strong local editing and branching
behavior without requiring durable transcript identity for ordinary work.

At the same time, broader transcript-parallelism and queue-shaped designs make
it more plausible that multiple journals, branch-local histories, or imported
worker histories will eventually need to combine into one coherent durable
history.

There is also a more direct storage pressure: one forever-growing hot
`events.jsonl` is an awkward long-term physical unit. Older history may want to
move into colder split segments and possibly compressed archival sets without
ceasing to be part of the durable record.

## Desired Reality

TOAS should remain LCP-first even if event histories multiply.

If additional merge provenance is needed, it should be introduced in the
smallest possible way, ideally by attaching limited ancestry-rebound metadata
only when new adopted message content is actually appended after an LCP
boundary.

## Pressure

This is a narrow but important architectural pressure:

- preserve mergeability across multiple journals or imported histories
- allow physical journal splitting for size and operational manageability
- allow older segments to be compressed or archived without semantic loss
- keep message-tree parentage simple and canonical
- avoid making transcript identity mandatory for ordinary stepping
- retain lightweight no-op transcript rebound behavior

The core question is not "how do we build merges now?" but:

```text
what extra durable provenance, if any, is justified without weakening LCP primacy?
```

## Evidence

- The 2026-06-26 design outline argues that transcript parallelism will create
  more situations where separate event histories later need to cohere.
- `docs/notes/2026-05-24-multi-active-transcript-surfaces-design.md` already
  shows that multi-surface stepping raises continuity and provenance questions
  once multiple authored surfaces share durable state.
- `docs/runtime-ownership.md` keeps durable state, transcript reconciliation,
  operator semantics, and projection/rendering distinct, which is exactly the
  split this design pressure needs.
- Operationally, split hot/cold journals and compressed archive sets are an
  attractive way to keep durable history manageable without discarding it.

## Open Questions

- Should rebound provenance live in message metadata, a parallel durable record,
  or remain absent until stronger evidence appears?
- Should segmented and compressed storage be transparent inside durable-state
  query APIs, or explicit at higher layers?
- What exact condition makes ancestry reachback meaningful rather than trivial?
- Should naked rebound with no new adopted message stay unrecorded by default?
- How should merged or imported histories preserve provenance without inventing
  durable transcript identity for normal single-surface use?

## Exit Evidence

This task can leave inception when one focused design slice becomes concrete
enough to specify and test.

Useful exit artifacts would be one or more of:

- a proposed rebound provenance schema with exact emission rules
- examples proving the schema helps merged-history interpretation without
  changing ordinary LCP-first stepping
- a storage-layout proposal for hot/cold segments and compressed archive sets
  that preserves one logical durable history
- a decision that message metadata is sufficient, or a justified reason it is
  not

## Notes

This task should stay deliberately conservative. The value is preserving TOAS's
lightweight transcript-first model while making room for richer merged-history
provenance only if real evidence demands it.

The storage-layout angle is part of the same pressure, but it should still be
framed as durable-state ownership and recoverability work rather than as an
excuse to loosen transcript or message-tree invariants.
