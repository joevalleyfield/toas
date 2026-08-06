Filed as: 260804-automatic-hot-journal-rollover
FKA:
AKA: automatic events.jsonl rotation; bounded hot journal; production segment rollover
Legacy index:

keywords: runtime, implementation, parked, performance, storage, graph, policy, boundaries

Parent: `260626-events-jsonl-multiplicity-and-merge-provenance`
Depends on: `260627-segmented-event-journal-storage-contract`; `260630-soft-rotation-scale-fixture`; `260627-split-storage-rebuild-and-projection-parity`
Related: `260803-session-rotation-lifecycle`; `260804-vim-session-rotate-handoff`

# Automatically Roll Over The Hot Event Journal

## Objective

Put a durable operational bound on the physical `.toas/events.jsonl` hot file
by automatically sealing it into the established ordered segment layout after
a configurable size threshold is crossed. Rotation must occur only after the
current turn is fully durable and must preserve one logical append-only event
history across sealed segments and the new hot journal.

This is automatic storage lifecycle. It must not compact, rename, replace,
suggest rotation for, or otherwise manipulate the user-visible transcript.

## Existing Foundation

- `260627-segmented-event-journal-storage-contract` defines one writable hot
  journal plus monotonically ordered sealed `.jsonl`/`.jsonl.gz` segments.
- `260630-soft-rotation-scale-fixture` proves that size pressure becomes visible
  only after a complete turn and explicitly leaves production rotation policy
  unimplemented.
- Segmented history/query work already reads sealed sources and the hot file in
  declared order, subject to each surface's hot/segment selection policy.

## Required Contract

- Add a durable/configurable hot-journal size threshold with a documented
  default and explicit disable/override behavior.
- Evaluate pressure after an atomic logical turn or equivalent safe persistence
  boundary; never split the records belonging to one step/run consequence.
- Seal the complete hot file under the next monotonic segment ordinal without
  overwriting, reordering, or ambiguously duplicating an existing segment.
- Rebuild or rotate derivative indexes consistently with the journal boundary.
- Create a fresh writable `.toas/events.jsonl` using the established empty-hot
  or self-contained-hot continuation contract.
- Recover deterministically from interruption before rename, after sealing, or
  before fresh-hot initialization; ambiguous layouts must fail closed.
- Keep sealed history recoverable through source-aware history, graph,
  transcript, fsck, index, and rebuild surfaces.
- Do not couple rollover to `/compact`, `:ToasRotate`, session naming, Vim
  buffers, or autonomous transcript continuation. The one permitted
  context-related input is the transient active-transcript guard below; it
  prevents size policy from repeatedly rolling over a journal that must remain
  hot-local for the current round-trippable transcript.

## Active-Transcript Guard

The configured hot-journal size is the normal soft rollover threshold. It is
not a hard ceiling when a completed LLM round trip establishes that the active
transcript needs more retained hot-journal space to remain viable.

After a completed generation is durably recorded, calculate a transient
protection floor from that round trip:

```text
protected bytes = 16 × (request input tokens + generated response tokens)
effective threshold = max(configured threshold, protected bytes)
```

The token count must cover both the request input and generated response: the
new assistant response is now part of the active transcript even though it was
not in the request that produced it. The 16-bytes-per-token factor is a
deliberately conservative allowance for normal JSONL framing (event fields,
provenance, timestamps, ids, and parentage), rather than retained raw tool
payloads. Full tool results that should not enter model context are stored and
sampled explicitly outside `events.jsonl`.

This guard is evaluated only for the current active transcript and is never
persisted as a configuration rewrite. Once an explicit continuation produces a
seed-only or seed-plus-handoff successor and that smaller transcript completes
a round trip, its protection floor replaces the prior one. If the hot file is
then over the configured threshold, normal post-turn soft rollover may proceed.

## Acceptance Criteria

- [ ] A tiny configured threshold triggers automatic rollover only after the
  complete crossing turn has landed durably.
- [ ] The effective threshold is `max(configured bytes, 16 × completed
  round-trip tokens)` so an active context-fitting transcript cannot cause
  repeated rollover solely because its journal framing exceeds an undersized
  configured limit.
- [ ] The active-transcript protection is transient: after an explicit
  seed-only or seed-plus-handoff continuation completes a smaller round trip,
  ordinary configured-threshold rollover can resume.
- [ ] The sealed filename uses the next valid ordinal and the new hot journal
  becomes the sole append target.
- [ ] Repeated automatic rollovers keep the hot file bounded while preserving
  complete ordered recovery across all segments.
- [ ] Index files and metadata cannot silently point into the wrong physical
  journal after rollover.
- [ ] Crash-point fixtures prove recoverable or explicit fail-closed behavior
  for each filesystem transition.
- [ ] Concurrent or duplicate rollover attempts cannot overwrite a segment or
  produce two segments with the same ordinal.
- [ ] Default hot-only and explicit broader history surfaces retain their
  documented selection semantics after rollover.
- [ ] User-visible transcript files and active session selection remain byte-for-
  byte unchanged by storage rollover.
- [ ] Config/help documentation clearly distinguishes automatic event-journal
  rollover from explicit semantic compaction and successor-session rotation.

## Non-Goals

- Automatically rotating or compacting the user-visible transcript.
- Choosing archive deletion, expiry, or retention policy.
- Compressing newly sealed segments in the same transaction unless required by
  an already-settled storage contract.
- Adding parallel operators, new heads, or merge semantics.
- Reopening the segmented-history semantic contracts already settled by the
  prerequisite tasks.

## Allowed Write Surfaces

- graph/storage lifecycle and segmented-journal helpers under `src/toas/`;
- persistence call sites needed to schedule rollover after safe boundaries;
- config parsing, serialization, help, and policy surfaces;
- index/rebuild/fsck adapters required for rollover correctness;
- focused storage, crash, concurrency, scale, and projection tests;
- segmented-storage documentation;
- this task and generated `tasks/WORKBOARD.md` sections.

## Required Completion Evidence

- settled default threshold and disable/override configuration surfaces;
- filesystem transition/state matrix including crash recovery;
- tiny-threshold single-turn and repeated-rollover fixtures;
- index/fsck/rebuild and source-selection parity results;
- proof that transcript/session files remain untouched;
- focused and full-suite results.
