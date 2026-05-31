# 662: Pre-572 Test Contract Cleanup And Functional Parity Hardening

## Goal

Stabilize and de-risk the current working test surface before executing `572` in earnest, with explicit focus on removing/rewriting overconstrained unit expectations that drift from transport/runtime truth.

## Why

Recent fixes exposed contract pressure where unit tests were asserting layer-local behavior that conflicts with cross-surface semantics. This increases risk of preserving accidental seams and makes refactors harder.

## Scope

- Audit changed/failing-sensitive tests in the current working area (daemon async runner, daemon wrappers, host stdio/session host, shell ops, Vim phase6 report).
- Classify each assertion as:
  - semantic contract (keep/strengthen)
  - compatibility projection (isolate + label)
  - implementation detail (remove/relax)
- Rewrite tests to assert behavior at correct ownership boundary.
- Add/upgrade functional tests where unit tests currently stand in for integration truth.
- Keep existing runtime behavior stable unless needed to restore coherent contract ownership.

## Non-Goals

- Full naming/terminology cleanup from `572`.
- Large runtime re-architecture.
- Backing out already-landed changes solely to satisfy legacy unit-shape assumptions.

## Done When

- Unit tests no longer force incompatible contracts across `async_runner` vs daemon projection boundaries.
- Critical stream/watch/subscribe behavior is validated by functional parity tests, not only seam-local assertions.
- Compatibility-only assertions are clearly marked and narrowly scoped.
- Focused + full `--no-cov` test runs pass.

## Proposed Workplan

1. Build a contract map for touched tests and runtime seams.
2. Tag tests by ownership level (producer, projection, transport, consumer).
3. Refactor brittle tests to contract-level assertions.
4. Add functional parity checks for same-run behavior across RPC watch and stdio subscribe.
5. Run focused suites, then full `uv run pytest --no-cov` baseline.
6. Record any residual risk and handoff notes for `663` + `572`.

## Progress Log

- 2026-05-31: Task opened as immediate precursor to `572` after identifying unit-test overconstraint risk in daemon/host stream seams.
