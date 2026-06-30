Filed as: 260630-soft-rotation-scale-fixture
FKA:
AKA: bounded hot log fixture; hot-size pressure test; soft rotation trigger
Legacy index:

keywords: graph, storage, hardening, follow-on, correctness, contract, testing

Parent: `260629-storage-scale-model-proof-contract`
Related: `260627-split-storage-rebuild-and-projection-parity`; `260630-history-scale-model-functional-tests`

# Soft Rotation Scale Fixture

## Current Reality

TOAS needs hot-size pressure because very large active event logs make ordinary
work unpleasant. The hot log is the active working set, not the whole archive,
but current scale-model fixtures still hand-construct segmented layouts instead
of proving rotation pressure as a lifecycle trigger.

The contract now says hot-size pressure is soft: it should request or schedule
rotation at a safe boundary, never stop durable writes mid-turn.

The operator should also have an explicit rotation action, likely `/rotate` or
similar, so lifecycle management is not only an automatic pressure response.

## Desired Reality

A tiny scale-model fixture can force rotation pressure with a deliberately low
hot-size trigger and prove the boundary behavior:

```text
the configured hot-size trigger is crossed during a turn
the whole turn still lands durably
rotation is requested or becomes eligible only after the turn is complete
```

That fixture should make hot-size pressure testable without requiring huge
histories.

## Scope

- define the smallest current/future-facing fixture for soft hot-size pressure
- use a tiny configurable threshold so tests can force rotation cheaply
- assert that multi-event turn persistence is not interrupted mid-turn
- assert that rotation state is requested, scheduled, or diagnostically visible
  only at a safe boundary
- account for explicit operator-requested rotation (`/rotate` or similar) as
  the same safe-boundary lifecycle path as size-pressure rotation
- connect the fixture to transcript rehydration and cold/hot continuation where
  useful

## Non-Goals

- implement full production rotation policy
- choose the final default hot-size threshold
- implement root-prefix stitching
- design new `/compact` options or assisted compaction modes
- design archive retention or deletion policy
- change graph/topology rendering

## Exit Evidence

- a focused test or fixture proves soft-trigger behavior at a tiny threshold
- the test distinguishes turn completion from post-turn rotation eligibility
- docs/task notes explain that the trigger protects active-work ergonomics
  without hiding or deleting durable history
- related scale-model tests still pass
