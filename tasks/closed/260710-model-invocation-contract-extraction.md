Filed as: 260710-model-invocation-contract-extraction
FKA:
AKA: generation runner contract extraction; resolved model invocation; generation outcome
Legacy index:

keywords: runtime, implementation, historical, maintainability, generation, boundaries, policy, provenance

Parent: `260710-step-generation-domain-boundary-contract`
Related: `260615-runtime-package-growth-boundary-audit`

# Model Invocation Contract Extraction

## Intent

Replace the cross-domain portion of `StepCliDeps` with explicit values at the
Effective Policy And Authority to Model Invocation boundary. Preserve current
step behavior while making `GenerationRunner` an owner of provider execution,
retry, response normalization, and model-call outcome facts rather than a
service locator consumer.

## Scope

- introduce a typed resolved invocation carrying shaped messages, provider
  settings, retry policy, and selection provenance
- introduce a typed generation outcome carrying the assistant message and
  model-call audit facts without hiding them under `_llm_call`
- extract request/context/policy resolution from `GenerationRunner` behind an
  explicit function or collaborator
- narrow model execution to true ports: provider invocation, audit persistence
  if still required during failed attempts, retry clock, and typed stream event
  observation
- preserve a compatibility assembly path while `run_step` and existing tests
  migrate
- leave a clear deletion path for generation-related fields on `StepCliDeps`

## Non-Goals

- redesign session persistence, transcript redaction, newline handling, or
  stdout rendering
- move frontier classification out of Operator Semantics
- change backend/model selection precedence, retry semantics, streaming
  behavior, durable record shape, or user-visible output
- reorganize the broader `runtime/` package

## Allowed Write Surface

- `src/toas/runtime/step_generation_runtime.py`
- one or more focused generation/policy contract modules under
  `src/toas/runtime/`
- `src/toas/runtime/step_context_runtime.py`
- `src/toas/runtime/step_generation_cli_edges.py`
- narrow compatibility edits in `src/toas/cli_session_commands.py`
- focused generation and CLI-session tests
- this task and generated workboard state

## Acceptance Criteria

- request resolution can be tested without constructing `StepCliDeps`
- model execution can be tested with a provider port and typed invocation,
  without session IO, rendering, transcript persistence, or CLI dependencies
- success and exhausted/permanent failure preserve current retry and model-call
  audit behavior, including source provenance
- streaming callbacks or events remain observational and do not alter the
  semantic invocation or outcome contracts
- `StepCliDeps` loses the generation request/result classes and the internal
  model-invocation implementation callbacks made obsolete by the new owner
- existing CLI, daemon, and acceptance behavior remains compatible

## Verification

- focused tests for invocation resolution, retry/failure audit, response
  normalization, and stream observation
- `./.codex-local/bin/uvt run pytest tests/test_cli_session_commands.py -q --no-cov`
- any daemon tests that monkeypatch the generation compatibility surface
- the relevant replay-only step acceptance slice when it selects tests

## Completion Evidence

- before/after inventory of generation-related `StepCliDeps` fields
- named tests demonstrating the policy-to-invocation and
  invocation-to-outcome contracts
- recorded focused test results and any acceptance deselection caveat

Completed 2026-07-10.

Before, `StepCliDeps` carried the private request-plan and execution-result
classes plus provider generation, error classification, model naming, and
stream-presenter callbacks. After, those concerns are owned by
`model_invocation_contracts.py`: `ResolvedModelInvocation` is the policy
handoff, `ModelInvocationPort` is the provider/environment port, and
`GenerationOutcome` carries normalized message plus model-call facts. The
legacy `_llm_call` dictionary remains only as a step-facing projection from the
typed outcome.

Evidence:

- `tests/test_model_invocation_contracts.py` covers request resolution without
  constructing `StepCliDeps` and the explicit provider port.
- `tests/test_cli_session_commands.py`, `tests/test_daemon.py`, and
  `tests/test_daemon_async_runner.py` preserve compatibility behavior.
- focused compatibility run: 94 passed
- full run: 2,636 passed, 9 deselected
- `ruff check` passed for changed source and tests
