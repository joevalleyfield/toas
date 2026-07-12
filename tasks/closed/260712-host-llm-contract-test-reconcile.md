Filed as: 260712-host-llm-contract-test-reconcile
FKA:
AKA: stale host llm integration expectations; event-only integration cleanup
Legacy index:

keywords: runtime, hardening, historical, contract, async, watch, cancel, stream, coverage

Parent: `260711-watch-chunk-contract-retirement`
Depends on: `260712-runtime-watch-chunk-removal`; `260705-cancel-timeout-terminality-contract`
Related: `260712-watch-adapter-contract-cleanup`; `260712-host-double-cancel-race-harness`

# Host LLM Contract Test Reconciliation

## Objective

Reconcile the remaining host-LLM stand-in integration expectations with the
landed event-only watch contract and two-stage cancellation contract.

## Scope

- assert terminal subscriber truth from terminal `push_complete` payloads
- replace the removed top-level `watch.chunk` assertion with semantic
  projection-event evidence
- make forced-cancellation coverage issue an explicit second cancel
- run the focused host integration file and full default suite

## Non-Goals

- production runtime changes
- changing cancellation or terminality semantics
- reopening the completed watch-chunk retirement design

## Exit Evidence

- [x] host-LLM stand-in integration file passes
- [x] full default suite passes
- [x] no integration test reads removed aggregate watch text
- [x] cancellation test language distinguishes graceful intent from escalation

## Completion Evidence

- terminal cancel coverage now resubscribes across
  `push_complete complete=false` and asserts terminal truth from the eventual
  `complete=true` payload
- reasoning-only completion asserts its warning from semantic projection
  deltas instead of removed top-level `watch.chunk`
- both cancellation-shape integrations now encode the two-stage contract:
  first cancel returns `cancelling`, second cancel forces `cancelled`
- added focused branch assertions for cancellation observation basis, closer
  failure tolerance, already-terminal return, and write-hook finalization
- focused host integration: `7 passed`
- full default suite: `2680 passed, 9 deselected`, 100% coverage
- no production files changed
