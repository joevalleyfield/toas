# 562: Post-561 Surface/Step Dispatch and CLI/Operator Refactor Follow-Through

## Why

Task `561` landed the multi-surface capability set quickly and correctly, but a red-green-refactor POV pass identified maintainability hotspots in the touched seams.

This follow-up captures those findings as explicit refactor work so we preserve momentum without letting branch-density and duplicated parsing drift into future regression risk.

## Goal

Reduce branch density and responsibility mixing in recently expanded `step`/`surface` CLI and operator seams while preserving behavior and coverage.

## Scope

- Extract command-line option parsing seams from `cli_dispatch` for `step`, `step --async`, and `surface` subcommands.
- Split `run_surface` command multiplexer in `cli.py` into focused local handlers.
- Centralize duplicated usage/error string literals for new `step`/`surface` surfaces.
- Clarify operator API outcome typing for surface commands (typed intent over reusing unrelated outcome names).

## Non-Goals

- Changing transcript/LCP lineage authority semantics.
- Introducing new runtime policy gates.
- Altering surface precedence behavior already covered by `561` tests.

## Findings Captured (From 561 POV Review)

1. `dispatch_main` branch density regrowth in `src/toas/cli_dispatch.py`.
2. `run_surface` mixed responsibilities in `src/toas/cli.py`.
3. Usage/error string duplication across dispatch/CLI seams.
4. Surface operator outcomes currently piggybacking generic outcome type names.

## Planned Work

1. Extract dedicated parse helpers in `cli_dispatch_ops`:
   - `parse_step_options`
   - `parse_step_async_options`
   - `parse_surface_options`
2. Decompose `run_surface` into focused `run_surface_*_local` handlers and a thin dispatcher.
3. Consolidate usage strings into shared constants close to dispatch/CLI parsing seams.
4. Introduce/align explicit operator outcome typing for surface operations.
5. Keep tests green with behavior parity assertions (no semantic drift).

## Acceptance Criteria

1. `cli_dispatch` complexity for `step`/`surface` branches is reduced via extracted helper seams.
2. `cli.py` surface command path is split into focused local handlers.
3. Duplicated usage strings for the touched surfaces are materially reduced.
4. Operator API surface outcomes use clear/intentional typing.
5. Existing `561` behavior and tests remain passing.

## Validation

```bash
uv run pytest tests/test_cli_dispatch.py tests/test_cli.py tests/test_operator_api.py -q --no-cov
```

## Related

- `561` multi-active transcripts as independent control surfaces over shared graph
- `374` baseline coverage-led refactor umbrella
- `379` coverage-noise burndown
- `400` module decomposition follow-through


## Completion Notes (2026-05-24)

- Extracted `parse_step_options`, `parse_step_async_options`, and `parse_surface_options` into `src/toas/cli_dispatch_ops.py` and rewired `dispatch_main` to consume them.
- Centralized `step`/`surface` usage strings in dispatch ops constants to reduce drift between dispatch and CLI guardrails.
- Split `run_surface` in `src/toas/cli.py` into focused local handlers: `_run_surface_list_local`, `_run_surface_bind_local`, `_run_surface_select_local`, `_run_surface_rebind_local`, with `run_surface` now as thin action dispatcher.
- Added explicit `SurfaceCommandOutcome` in `src/toas/operator_api.py` and moved `bind_surface`/`select_surface`/`rebind_surface` to return that typed outcome rather than reusing `HeadOutcome`.
- Preserved behavior parity for existing command surfaces and error shapes while reducing branch density and responsibility mixing.

## Validation Evidence

```bash
uv run pytest tests/test_cli_dispatch.py tests/test_cli.py tests/test_operator_api.py -q --no-cov
```

Result: `231 passed`

## Status

Closed.
