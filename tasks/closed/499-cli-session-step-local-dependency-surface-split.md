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

## Progress
- first extraction slice landed in `cli_session_commands.py` by splitting `run_step_local(...)` setup/dependency assembly into focused helpers:
  - `_prepare_session_transcript(...)` for session-path resolution + stdin/control transcript injection + newline normalization
  - `_build_runtime_context(...)` for head/log/lineage/cwd/workspace/bind/anchor context assembly
  - `_build_step_kwargs(...)` for reflective step-arg wiring and already-executed index projection
- `run_step_local(...)` now delegates these setup phases and remains focused on execution/persistence/side-effects flow.
- targeted parity validation:
  - `uv run pytest tests/test_cli_session_commands.py tests/test_cli.py -q --no-cov` (`163 passed`)
- second extraction slice split config/settings/generation-runner assembly out of `run_step_local(...)` into `_resolve_runtime_generation_context(...)`.
- the helper now owns:
  - discovered file/session config merge and source mapping
  - runtime settings resolution and generation policy shaping
  - `GenerationRunner` + stream-state construction
- `run_step_local(...)` now delegates configuration/dependency assembly and remains focused on transcript/context execution and persistence flow.
- targeted parity validation rerun:
  - `uv run pytest tests/test_cli_session_commands.py tests/test_cli.py -q --no-cov` (`163 passed`).
- third extraction slice split post-step persistence/side-effect/output flow from `run_step_local(...)` into `_persist_step_outputs(...)`.
- the helper now owns append/result split, transcript redaction writeback, message/llm persistence, frontier record stitching, result side-effects, and final stdout emission.
- `run_step_local(...)` is now primarily orchestration: prep transcript/context/config, execute step, delegate persistence/output.
- targeted parity validation rerun:
  - `uv run pytest tests/test_cli_session_commands.py tests/test_cli.py -q --no-cov` (`163 passed`).

## Closure Audit
- AST/function survey confirms `run_step_local(...)` is now a thin orchestration seam (49 lines) delegating setup/dependency/execution-output responsibilities to focused helpers.
- helper seams now cover transcript prep, runtime context assembly, runtime generation context resolution, reflective step-kwargs assembly, and post-step persistence/output flow.
- scope check: remaining larger module hotspot is `GenerationRunner`, which is outside this task's explicit objective (this task is run_step_local seam-splitting).

## Final Validation
- targeted parity: `uv run pytest tests/test_cli_session_commands.py tests/test_cli.py -q --no-cov` (`163 passed`)
- full suite: `uv run pytest` (`1362 passed`)

## Status
- [x] complete
