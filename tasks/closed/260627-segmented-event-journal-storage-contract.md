Filed as: 260627-segmented-event-journal-storage-contract
FKA:
AKA: hot/cold event journals; archive segments; event-log sharding
Legacy index:

keywords: docs, exploration, historical, contract, storage, boundaries, provenance, append-only

Parent: `260626-events-jsonl-multiplicity-and-merge-provenance`
Related: `260614-architecture-follow-through-coordination`

# Segmented Event Journal Storage Contract

## Current Reality

TOAS currently treats `.toas/events.jsonl` as one flat append-only physical
unit. That is simple, but it makes size, rollover, and cold-history management
all somebody else's problem.

## Desired Reality

One logical durable history should be able to span:

- one hot append target
- older cold segments
- optionally compressed archival segments

without changing append-only semantics or requiring callers to invent their own
storage interpretation.

## Scope

- define physical layout for segmented event journals
- define hot vs cold segment meaning
- define rollover expectations
- define what "compressed but still durable" means operationally
- define recoverability and ordering invariants

## Non-Goals

- implementing graph query changes
- designing new provenance metadata
- adding merge UX

## Exit Evidence

- a concrete storage-layout contract suitable for graph/query implementation
- explicit invariants for append target, cold segments, and archive semantics
- clear statement of what metadata identifies segment order and recoverability

## Outcome

Closed. `docs/notes/2026-06-27-segmented-event-journal-storage-contract.md`
now fixes the first segmented-storage contract:

- `.toas/events.jsonl` remains the sole hot writable append target
- LCP reconciliation is explicitly hot-only
- hot storage must remain self-contained and rooted back to `n1`
- sealed older history moves under `.toas/segments/` as monotonic ordinal
  segments
- cold segments stay plain `.jsonl`, archival segments may be `.jsonl.gz`
- filename ordinals define logical read order, with the hot file always last
- gaps, duplicate ordinals, or ambiguous duplicate sealed forms are explicit
  invalid states rather than stitched heuristically

That gives the next graph/query hardening slice a concrete physical layout and
recoverability contract to target without prematurely committing to manifests,
merge provenance, or segment-backed reconciliation.
