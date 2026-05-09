# 489 Daemon Self-Shell Elimination via Operator API

## Objective
Eliminate daemon/runtime subprocess paths that shell out to `toas` itself where direct operator API calls can provide equivalent behavior.

## Why
With core 470 seam work in place and 469 closed, remaining high-value motivation is runtime simplification:
- reduce redundant process hops
- improve latency and streaming consistency
- reduce behavioral divergence across warm/cold/CLI paths
- simplify failure handling and observability

## Scope
In scope:
- audit daemon/runtime paths for self-shell subprocess invocation patterns (`uv run toas ...` / `toas ...`)
- classify each path:
  - must remain subprocess (isolation/cancellation contract)
  - eligible for operator API replacement
- migrate at least one high-value eligible path to direct operator API use with parity tests

Out of scope:
- removing subprocess usage that is contractually required for cancellation/isolation
- broad redesign of daemon protocol surfaces

## Deliverables
- inventory of self-shell call sites and disposition
- one or more migrated paths using operator API seams
- parity/regression tests for migrated paths
- notes on any retained subprocess paths and rationale

## Done When
- at least one meaningful self-shell path is removed in favor of operator API
- migrated path has explicit parity tests
- remaining retained self-shell paths are documented with rationale

## Related
- 470 operator API seam and CLI-thin wrapper migration
- 483 command stdout streaming to Vim plugin (closed)
- 485 shell-lane purpose unification (closed)
