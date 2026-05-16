# 518 Envelope Adoption Expansion Beyond Watch

## Objective
Extend envelope-aware protocol handling beyond watch flow so async step lifecycle paths (`step_async`, `cancel`, and terminal status shaping) share one adapterized envelope contract while preserving current CLI/Vim-visible behavior.

## Why
`515` and `517` established envelope semantics and watch-path adoption. The next simplification step is to reduce legacy-shape coupling in adjacent async lifecycle flows, so transport/protocol evolution does not stall at one endpoint.

## Scope
- define adapterized envelope shaping for async lifecycle responses adjacent to watch
- apply envelope-first/legacy-compatible handling to one additional production path beyond watch
- preserve existing user-visible outputs and existing request/response op names
- add focused parity tests proving no behavioral regressions

## Out of Scope
- daemon removal
- full protocol big-bang conversion
- front-end specific UX changes

## Done When
- at least one non-watch async lifecycle path uses envelope adapterized shaping
- CLI consumers remain output-compatible
- tests cover envelope + legacy parity for the migrated path
- roadmap reflects post-517 envelope adoption progress

## Initial Slices
1. Inventory async lifecycle responses (`step_async`, `watch`, `cancel`) and select next migration seam.
2. Add/extend adapter helper(s) for selected seam.
3. Wire one production path through adapter with legacy parity retained.
4. Add focused tests + full-suite validation.

## Related
- `515` protocol envelope v0 + durability map (closed)
- `517` transport abstraction + watch adapterization (closed)
- `484` watch protocol semantics
- `470` operator API seam migration

## Progress
- completed slice 1 inventory:
  - reviewed async lifecycle response seams across `step_async`, `watch`, and `cancel`
  - selected non-watch migration target:
    - lifecycle response shaping for `step_async` + `cancel`
- completed slices 2/3 initial wiring:
  - added lifecycle envelope adapter:
    - `src/toas/runtime/async_lifecycle_envelope_adapter.py`
  - wired daemon async lifecycle responses:
    - `src/toas/daemon/async_runner.py` (`step_async` start response)
    - `src/toas/daemon/run_store.py` (`cancel` responses)
  - wired CLI consumer fallback:
    - `src/toas/cli_async_commands.py` now reads `envelope.payload.status` first for lifecycle status, then legacy `status`
