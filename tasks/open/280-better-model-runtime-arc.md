## Goal

Harden the model runtime: bounded retries, clearer error classes, richer `llm_call` records, and the foundations for multi-backend support.

## Why Now

The current generation path fails fast with a `SystemExit` on any error. There is no retry, no error classification, and no way to distinguish transient failures from permanent ones. As sessions get longer and more mechanical workflows depend on generation, a fragile runtime becomes increasingly costly.

## Scope

- `281`: bounded retries with explicit error classes — classify generation errors, retry transient failures up to a configurable limit, record each attempt
- `282`: richer `llm_call` records and multi-backend foundations — latency, token counts where available, and a clean seam for a second backend shape

## Intended Inputs

- `llm.py` generation path
- `llm_call` record shape in `graph.py`
- `OperatorConfig` for retry and timeout knobs
- `BackendGenerationPolicy` / `GenerationPolicy` from `261`

## Intended Outputs

- generation path that retries on transient failures with a configurable cap
- error classes that are inspectable and recordable
- `llm_call` records with at minimum latency and a success/failure/retry summary
- documented seam for adding a second backend shape

## Constraints

- default behavior (no retries beyond current) must be preserved at default config
- retry count and backoff must be config-settable via `OperatorConfig`
- each retry attempt should produce its own `llm_call` record, not overwrite the prior

## Done When

- `281` and `282` are closed
- transient generation failures retry rather than abort
- `llm_call` records carry richer metadata
- multi-backend seam is documented even if only one backend is wired
