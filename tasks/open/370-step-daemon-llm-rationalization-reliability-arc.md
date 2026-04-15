# 370: Step/Daemon/LLM rationalization and reliability arc

- **Status**: Open

## Summary

Recent fixes addressed concrete reliability defects (runtime stream-policy selection, warm-path process-state mutation serialization, and client cache locking), but the core execution surfaces remain overly coupled and large.

Primary hotspots are:
- `src/toas/cli.py:run_step_local` and nested `generate()` (configuration, retry policy, streaming presentation, llm durability, and step persistence mixed together)
- `src/toas/daemon.py:handle_request` (branch-heavy op dispatch with repeated error wrappers)
- `src/toas/llm.py:call_backend` (transport, stream chunk extraction, debug taps, and normalization combined)

This arc should reduce cognitive load, shrink blast radius for changes, and increase deterministic test coverage for runtime behavior.

## Action

1. Extract step-local execution seams.
- Introduce execution context + generation runner boundaries for `run_step_local`.
- Move backend/model selection and retry/error-context shaping into pure helpers.
- Keep `run_step_local` as orchestration over clearly named sub-steps.

2. Split streaming presentation from generation.
- Move prompt-progress/thinking/content terminal rendering state machine out of generation logic.
- Keep generation callbacks as normalized events; keep CLI projection policy local and testable.

3. Refactor daemon op routing.
- Replace `if/elif` op chain with an operation registry and shared error-mapping wrapper.
- Keep workdir/process-state rules explicit and locally testable.

4. Isolate llm protocol adapters.
- Split stream chunk parsing/debug collection from transport invocation.
- Keep a narrow `BackendResponse` normalization seam.

5. Add reliability-focused tests.
- Retry/error-classification + `llm_call` persistence tests in CLI path.
- Streaming interleave tests (prompt-progress -> reasoning -> content transitions).
- Daemon concurrent request tests for warm async/status/watch/cancel interactions.
- Local-vs-daemon parity smoke tests for persisted records and stdout contracts.

## Guardrails

- Preserve history and projection invariants from `AGENTS.md`.
- Treat daemon/vim transport as optimization only; preserve local semantic parity.
- Land in small commits with task-file stitching per milestone.

## Progress

- Task opened with concrete smell inventory and staged implementation plan.
- Stage-1 extraction landed in `src/toas/cli.py`:
  - introduced private `_GenerationRunner` with explicit stages:
    - `prepare_request(...)`
    - `execute_with_retry(...)`
    - `build_artifacts(...)`
  - `run_step_local()` now wires `step(..., generate=...)` through `_GenerationRunner.generate`
  - behavior target is parity-only (no intentional runtime contract changes)
- Stage-2 extraction landed in `src/toas/cli.py`:
  - introduced private `_StreamPresenter` for prompt-progress/thinking/content stream projection behavior
  - `_GenerationRunner._call_model_once` now delegates callback-side projection state transitions to `_StreamPresenter`
  - added focused presenter tests in `tests/test_cli.py` for prompt-progress dedupe/diagnostics and thinking-close-on-content transitions
- Stage-3 extraction landed in `src/toas/daemon.py`:
  - `handle_request` now routes through an operation-handler registry with shared error mapping
  - preserved special async-op `op_error` payload detail (`...\\npayload={...!r}`) for `step_async*` starts
  - default operation path remains routed through `_run_op_capture_stdout` under `_request_workdir`
  - validated against existing daemon routing tests in `tests/test_daemon.py`
- Stage-4 extraction landed in `src/toas/llm.py`:
  - stream processing moved behind focused adapter helpers (`_stream_backend_response`, `_process_stream_chunk`, `_handle_stream_progress`, `_extract_usage_dict`)
  - `call_backend` now uses stream/non-stream orchestration with smaller branch surface
  - added stream-state test coverage in `tests/test_llm.py` for latest model/usage accumulation behavior
