# 499 CLI Session Step Local Dependency Surface Split

## Objective
Refactor `src/toas/cli_session_commands.py` so `run_step_local` dependency resolution and execution-phase responsibilities are split into explicit helper seams.

## Why
`run_step_local` remains a high-complexity seam touching config/runtime/operator paths and is a frequent coupling point for daemon/operator API callers.

## Scope
- extract dependency construction and execution-phase helpers from `run_step_local`
- reduce inline branching in `run_step_local` while preserving current stdout/session contracts
- keep caller interfaces stable (`cli.py`, `operator_api.py`, daemon async lane)
- add targeted tests for new helper seams

## Out Of Scope
- changing CLI command semantics
- changing daemon watch protocol behavior

## Done When
- `run_step_local` is thinner and delegates to focused helpers
- caller behavior remains parity-safe
- targeted parity tests and full suite pass

## Related
- `400` decomposition umbrella
- `470` operator API seam and CLI-thin migration
- `489` daemon self-shell elimination follow-through
