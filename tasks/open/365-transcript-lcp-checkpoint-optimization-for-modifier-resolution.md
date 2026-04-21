## Goal

Optimize transcript-modifier resolution (`/shell`, `/env`, related command-derived state) using LCP/checkpoint state recovery plus tail replay.

## Status Note

Deferred. Keep open, but do not schedule implementation until modifier correctness work is explicitly complete.

## Why Now

Correctness fixes should land first, but full transcript rescans each step are unnecessary once we can recover effective state at a known checkpoint and apply only tail deltas.

## Scope

- define checkpoint state shape for modifier-derived effective runtime state
- recover modifier state at bind/LCP or nearest prior checkpoint
- replay only tail modifier commands to frontier
- preserve exact behavior parity with correctness-first implementation
- benchmark and document expected performance and replay-scale wins

## Intended Behavior

- modifier resolution remains semantically identical to full replay
- step-time overhead scales with tail size rather than full transcript size

## Constraints

- no hidden mutable semantics outside durable history
- checkpoint data must be reconstructible and auditable
- optimization must not change user-visible behavior

## Done When

- checkpoint/tail approach is implemented and tested against full-replay parity
- performance improvement is measured and documented
