Filed as: 261006-clarify-execution-generation-facets
FKA:
AKA: execution vs generation backend taxonomy; backend in generation; clean execution facet
Legacy index:

Parent: `260912-config-show-effective-overview`
Related: `260912-config-execution-facet-design`; `260912-config-show-navigation-and-model-view`

keywords: config, execution, generation, taxonomy, historical

# Clarify Execution and Generation Facet Boundaries

## Intent

Resolve conflation around the term "backend" across config topics by moving
model-server / inference settings (`backend.mode`, `backend.managed_local`) to
`generation` (synonymous with inference), keeping task runner / lifecycle
settings (`runtime.async_backend_mode`, `runtime.async_runs`,
`runtime.cancellation_mode`) in `runtime`, and focusing `execution` strictly on
action execution (assistant shell command bounds and tool write mutations).

## Scope & Boundaries

- In `_config_overview`, move `backend mode` from `execution:` to `generation:`.
- In `_config_execution_overview`, present only true execution concerns:
  `shell.assistant_timeout_s`, `shell.allowed_commands`, and
  `tool_writes.newline_style`.
- In `src/toas/assets/help/config.yaml`:
  - `generation`: add `backend.mode` and `backend.managed_local` to related keys.
  - `execution`: limit related keys to `shell.assistant_timeout_s`,
    `shell.allowed_commands`, and `tool_writes.newline_style`.
- Update tests and acceptance coverage to reflect the focused boundary.
- Maintain 100.00% statement coverage across all test suites.

## Progress

- 2026-10-06: Task opened following discussion on disambiguating the term "backend"
  between model server/inference lifecycle (which belongs with `generation`) and task
  orchestration (which remains in `runtime`).
- 2026-10-06: Disambiguated `generation`, `runtime`, and `execution` facets:
  - Moved `backend mode` into `generation:` in `_config_overview`.
  - Added `backend.mode` and `backend.managed_local` to `generation` related keys in
    `src/toas/assets/help/config.yaml`.
  - Restricted `execution` in `config.yaml` and `_config_execution_overview` strictly
    to action execution: `shell.assistant_timeout_s`, `shell.allowed_commands`, and
    `tool_writes.newline_style`.
  - Retained task execution lifecycle (`runtime.async_backend_mode`,
    `runtime.async_runs`, `runtime.cancellation_mode`) in `runtime`.
  - Updated all acceptance and unit test assertions; full check suite passing at 100.00%
    statement coverage (22,234 statements).

## Status

Complete.
