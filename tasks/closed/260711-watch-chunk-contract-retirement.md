Filed as: 260711-watch-chunk-contract-retirement
FKA:
AKA: watch chunk retirement; event-only watch contract; stream chunk compatibility removal
Legacy index:

keywords: runtime, migration, historical, contract, compatibility, stream, watch, transport, vim

Parent: `260614-architecture-follow-through-coordination`
Related: `260705-host-subscribe-terminal-event-parity`; `260705-cancel-timeout-terminality-contract`; `260710-vim-run-wrapper-and-inner-panels`

# Watch Chunk Contract Retirement

## Why This Exists

The current async watch surface still emits both:

- semantic `events`
- aggregate text `chunk`

But that is no longer an honest expression of the system's own contract.

The runtime now treats events as the authoritative semantic stream, while
`chunk` survives as a compatibility surface for older consumers. Because TOAS
owns both sides of that contract, this compatibility stance is increasingly
self-imposed drag rather than a real interoperability requirement.

Recent Vim cancel/finalization debugging made the cost concrete:

- terminal `watch` already contained the needed data in `events`
- Vim terminal reconciliation still looked primarily at `chunk`
- a later resubscribe replay made it appear as if missing data had arrived
  late, when in fact it had already been available semantically

That is a sign of contract deadlock: we say events are primary, but keep enough
`chunk` behavior around that consumers never have to fully move.

## Desired Reality

TOAS should converge on an event-only streaming/watch contract:

- `events` are the sole semantic payload for watch/follow/subscribe consumers
- `chunk` is neither produced nor consumed by first-party surfaces
- host bridges do not synthesize compatibility text projections when semantic
  events already exist
- Vim/CLI/runtime tests prove event-only semantics directly instead of
  tolerating dual-path parity

## Scope

- identify remaining first-party `chunk` producers and consumers
- retire Vim-side `chunk` consumption in favor of event-only reconciliation
- retire host-side compat projection/synthesis paths that exist only to keep
  `chunk` alive
- retire CLI/runtime compatibility reads that still special-case aggregate text
- remove runtime `watch.chunk` production once no first-party consumer needs it

## Non-Goals

- third-party compatibility promises TOAS does not actually make
- unrelated streaming UX redesign
- broad lane/dashboard work beyond what `chunk` retirement directly touches

## Proposed Landing Order

1. `260712-vim-event-only-watch-consumer`: Vim becomes event-only for
   render/finalization/reconciliation.
2. `260712-watch-adapter-contract-cleanup`: first-party CLI and host adapter
   contracts stop naming, reading, or documenting aggregate watch text.
3. `260712-runtime-watch-chunk-removal`: runtime stops emitting top-level
   `watch.chunk` and disposes of the coupled byte-offset contract explicitly.

These children are deliberately ordered. Removing the producer first would
turn remaining consumer assumptions into silent data loss; retaining the
producer after all first-party reads are gone gives the final change a narrow,
machine-checkable blast radius.

## Dispatch Notes

- This task owns the event-only target contract and the inventory of gaps. It
  should not become the implementation bucket.
- Generic transport/model variables named `chunk` are not part of this
  retirement. The target is specifically aggregate text on watch responses and
  compatibility projections derived from it.
- The host currently appears to ignore eventless watch chunks rather than
  synthesize them. The adapter child must certify that observed state and
  remove stale compatibility documentation/tests; it should not invent a host
  rewrite if no producer remains.
- `next_offset`/request `offset` are coupled to aggregate output bytes even when
  consumers render events. Their final disposition belongs to the runtime
  removal child and must be explicit rather than accidentally preserved.

## Exit Evidence

- [x] first-party watch/subscribe consumers no longer read `chunk`
- [x] first-party runtime/host layers no longer synthesize compat chunk paths
- [x] runtime no longer emits top-level `watch.chunk`
- [x] tests assert event-only streaming semantics without dual-path fallback
- [x] each implementation child records focused commands and passing evidence
- [x] the parent is closed only after all three children are closed

## Completion Evidence

- Vim event-only migration: 46 Vader cases and 147 assertions passed.
- CLI, host, subscribe, parity, and envelope adapter cleanup: 134 focused
  tests passed.
- Runtime producer removal and cursor contract: 154 focused tests passed.
- The final offset disposition is an opaque output-length wakeup watermark;
  semantic replay uses only event sequence cursors.
