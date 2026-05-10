# 503 Daemon Run Store Watch Async Step Phase Split

## Objective
Decompose `src/toas/daemon/run_store.py::watch_async_step` into explicit poll/follow phase helpers while preserving protocol semantics.

## Why
`watch_async_step` (~102 lines) remains a top daemon hotspot after protocol fixes and is central to streaming responsiveness behavior.

## Scope
- split initial snapshot/drain logic, incremental poll loop, and terminal completion shaping
- preserve poll/follow contract and no-timing-hack protocol semantics
- add focused tests for both poll/follow helper phases

## Done When
- `watch_async_step` delegates cohesive helpers and is materially slimmer
- daemon run-store tests validate helper-branch parity
- targeted parity and full suite pass

## Related
- `400` decomposition umbrella
- `484` watch protocol poll vs follow semantics
- `483` streaming to vim closure baseline
