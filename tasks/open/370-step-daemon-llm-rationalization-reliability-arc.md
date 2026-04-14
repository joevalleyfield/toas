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
