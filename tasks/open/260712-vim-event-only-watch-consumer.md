Filed as: 260712-vim-event-only-watch-consumer
FKA:
AKA: Vim watch event migration; Vim chunk fallback removal
Legacy index:

keywords: surface, migration, active, contract, watch, stream, vim, parity

Parent: `260711-watch-chunk-contract-retirement`
Related: `260705-host-subscribe-terminal-event-parity`; `260710-vim-run-wrapper-and-inner-panels`

# Vim Event-Only Watch Consumer

## Objective

Retire top-level watch chunk consumption from Vim.

## Context

Every first-party Vim watch path must render, reconcile, backfill, and finalize
from semantic events. This is the first landing slice because production cannot be retired
safely while Vim still has chunk-only collection, terminal backfill, or manual
watch fallbacks.

## Scope

- migrate synchronous async-step collection to event text
- remove top-level watch chunk fallback from timer-driven rendering
- make terminal backfill/catch-up event-only
- make manual watch/follow views event-only
- update Vim fixtures so meaningful output is represented by lane/phase-scoped
  semantic events, including mid-run, final projection, tool, reasoning,
  progress, cancellation, and reconnect cases
- preserve wire-level byte chunks used to frame stdio; those are transport
  reads, not the watch response contract being retired

## Allowed Write Surfaces

- `vim/plugin/toas.vim`
- `tests/vim/`
- Vim-focused test drivers under `tests/`
- this task file for progress and completion evidence

Changes outside these surfaces require the task to be re-scoped before work
continues.

## Acceptance Criteria

- [ ] no Vim watch response path reads top-level `payload.chunk`
- [ ] event text extraction accepts only the documented semantic event shapes;
  compatibility `payload.chunk` inside an event is removed unless separately
  justified as a non-watch protocol field
- [ ] empty-event watch responses never fabricate visible text
- [ ] terminal success/failure/cancel reconciliation remains correct when every
  watch response omits `chunk`
- [ ] poll, follow, and local-host subscribe paths render equivalent semantic
  events without duplicate text after replay/resubscribe
- [ ] stdio framing tests that use local variables named `chunk` remain intact
  unless their behavior genuinely changes

## Required Completion Evidence

- focused Vader/driver commands covering poll, follow, local-host subscribe,
  terminal backfill, cancel, and replay deduplication
- a repository search showing no top-level watch `chunk` read remains in Vim
- a concise note identifying any retained `chunk` spelling and why it is not
  part of the watch response contract
