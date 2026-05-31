# Phase B Runtime Ownership Migration Notes

Status: CURRENT
Scope: async lifecycle/runtime ownership seam guidance
Related tasks: `572`, `663`

## Intent

These notes are secondary to code-level guardrails and parity tests.
Primary defense remains explicit boundary patterns plus transport parity assertions.

## Ownership Pattern (Authoritative)

- Runtime modules own async lifecycle semantics.
- Daemon modules are compatibility transport adapters unless explicitly documented otherwise.
- New semantic logic should land in runtime-owned modules first.

## Current Phase B Mapping

- Async store implementation:
  - canonical: `src/toas/runtime/async_activity_store_impl.py`
  - compatibility alias: `src/toas/daemon/run_store.py`

- Async step worker implementation:
  - canonical: `src/toas/runtime/async_step_runtime_worker.py`
  - compatibility alias: `src/toas/daemon/async_runner.py`

## Guardrail Rules

- Do not add new semantic behavior to daemon alias modules.
- Treat daemon alias modules as import-compat surfaces only.
- Keep producer-vs-projection boundaries explicit, matching `663` contract style.
- Require parity-focused tests when moving seams:
  - daemon/watch and host/subscribe semantics must remain equivalent in lane/phase/payload/terminal meaning.

## Sunset Criteria

Compatibility aliases can be removed when all are true:

1. Runtime-owned imports are canonical across daemon facades/tests/callers.
2. No monkeypatch/test identity dependence remains on daemon path module objects.
3. Transport parity suites remain green without daemon alias path usage.
