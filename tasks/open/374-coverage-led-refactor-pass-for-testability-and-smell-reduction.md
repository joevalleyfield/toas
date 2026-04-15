## Goal

Run a focused coverage-led refactor pass that improves testability and uses uncovered seams to expose and address code smells we have deferred.

## Why Now

Coverage trend has been slipping while complexity has accumulated in high-churn runtime paths. Using targeted tests as the forcing function is the fastest way to improve reliability and reveal architectural cleanup priorities.

## Scope

- establish a prioritized low-coverage target list in `src/toas` (start with high-complexity/high-churn modules)
- add focused tests that lock intended behavior at seam boundaries before refactoring internals
- refactor for testability where needed (smaller units, clearer boundaries, lower closure/state coupling)
- document code smells uncovered during the pass and either fix them or open follow-on tasks immediately
- keep behavior and durable-history invariants unchanged

## Intended Behavior

- coverage improves in targeted modules
- newly added tests are deterministic and scenario-focused rather than snapshot-heavy
- refactors reduce cognitive load and make failure modes easier to isolate

## Constraints

- no semantic drift in transcript/history contracts
- no broad speculative rewrites; iterate in small validated slices
- each material change stays stitched to this task and roadmap focus

## Done When

- targeted module list is completed or explicitly triaged into follow-on tasks
- coverage rises in touched areas with passing test suite
- at least one concrete deferred smell is resolved or split into a tracked follow-up task
