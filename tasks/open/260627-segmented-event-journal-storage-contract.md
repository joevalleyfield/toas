Filed as: 260627-segmented-event-journal-storage-contract
FKA:
AKA: hot/cold event journals; archive segments; event-log sharding
Legacy index:

keywords: graph, exploration, inception, contract, storage, boundaries, provenance, append-only

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
