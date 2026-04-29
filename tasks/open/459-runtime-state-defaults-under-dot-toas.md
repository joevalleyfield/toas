## Goal

Move default runtime state paths under `.toas/` so operational artifacts live in one project-local hidden directory by default.

## Why

- Reduce root-directory clutter and ignore complexity.
- Align with config-layering direction (`458`) and session-path controls (`456`).
- Keep transcript location flexible while making default state placement coherent.

## Scope

- inventory current runtime files written at project root (for example: `events.jsonl`, `events.idx`, pid/socket artifacts, and related runtime state)
- define default path migration to `.toas/` equivalents
- keep transcript path independently configurable (can remain outside `.toas/`)
- preserve compatibility/fallback behavior for existing repos until migration is explicit

## Constraints

- no history mutation
- no behavioral regressions for daemon/CLI contracts
- clear migration strategy with compatibility reads where needed

## Done When

- default writes for runtime state use `.toas/` paths
- compatibility reads maintain old-root projects without breakage
- docs and help text reflect the new default layout
- tests cover both new defaults and legacy fallback behavior

## Planned Slices

1. Runtime state path inventory + central path resolver.
2. Durable history/index path migration with compatibility fallback.
3. Daemon pid/socket/state path migration.
4. Docs + migration notes.

## Progress

- opened

## Progress

- slice 1 groundwork landed: centralized event-path resolver seam in CLI/session command flows (`resolve_events_path`) with no behavior breakage.
- CLI/session command call sites now consume the shared resolver rather than direct path constants, reducing migration risk for follow-on slices.
- full-suite validation after slice: `1170 passed`, total coverage `92.53%`.
- slice 2 landed with explicit migration policy: `TOAS_RUNTIME_STATE_LAYOUT=dot_toas` prefers `.toas/events.jsonl` while preserving legacy-root fallback when `events.jsonl` already exists
- index rebuild now writes adjacent to the active events file (`events.idx` or `.toas/events.idx`) and reports the concrete path in output
- added dual-path tests for resolver behavior and dot-toas index rebuild path
- full-suite validation after slice: `1173 passed`, total coverage `92.53%`
- slice 3 landed with opt-in daemon/runtime state layout: when `TOAS_RUNTIME_STATE_LAYOUT=dot_toas`, pid/vim-port/socket defaults move under `.toas/` (`.toas/toas.pid`, `.toas/toas.vim-port`, `.toas/toas.sock`)
- added focused tests for daemon process-control paths and unix RPC default endpoint under dot-toas layout
- full-suite validation after slice: `1175 passed`, total coverage `92.54%`
