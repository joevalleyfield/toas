Filed as: 260711-watch-chunk-contract-retirement
FKA:
AKA: watch chunk retirement; event-only watch contract; stream chunk compatibility removal
Legacy index:

keywords: runtime, migration, follow-on, contract, compatibility, stream, watch, transport, vim

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

1. Vim becomes event-only for render/finalization/reconciliation.
2. Host subscribe/watch adapters stop projecting compat chunk-derived events.
3. CLI/watch consumers drop remaining chunk fallbacks.
4. Runtime stops emitting top-level `watch.chunk`.

## Exit Evidence

- [ ] first-party watch/subscribe consumers no longer read `chunk`
- [ ] first-party runtime/host layers no longer synthesize compat chunk paths
- [ ] runtime no longer emits top-level `watch.chunk`
- [ ] tests assert event-only streaming semantics without dual-path fallback
