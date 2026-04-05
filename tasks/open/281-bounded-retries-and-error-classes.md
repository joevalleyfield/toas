## Goal

Replace the current fail-fast generation path with bounded retries and explicit error classification, so transient backend failures do not abort the session.

## Why Now

`generate_assistant_message` raises on any error and `cli.py` converts it to a `SystemExit`. There is no distinction between a transient network hiccup and a permanent configuration error. In a mechanical workflow, a single transient failure forces a full manual restart.

## Scope

- define an error taxonomy in `llm.py`:
  - `TransientGenerationError`: timeout, connection reset, rate limit — safe to retry
  - `PermanentGenerationError`: auth failure, invalid request, model not found — do not retry
  - existing `Exception` handling routes into this taxonomy
- add `generation.max_retries: int` (default `0`, preserving current behavior) to `GenerationPolicy` in `OperatorConfig`
- add `generation.retry_delay_s: float` (default `1.0`) for inter-retry wait
- retry loop in `cli.py` `generate()`:
  - attempt up to `max_retries + 1` times
  - write a `llm_call` record for each attempt (success or failure)
  - on permanent error, abort immediately regardless of retry budget
  - on exhausted retries, raise `SystemExit` with a summary of attempts
- classify known OpenAI client error types; treat unknown errors as transient by default

## Intended Inputs

- `generate_assistant_message` in `llm.py`
- `GenerationPolicy` / `OperatorConfig` from `261`
- `write_llm_call_record` in `graph.py`

## Intended Outputs

- `TransientGenerationError` and `PermanentGenerationError` in `llm.py`
- retry loop in generation path
- per-attempt `llm_call` records
- tests covering: zero retries (default), successful retry after transient, permanent error aborts immediately, retry budget exhaustion

## Constraints

- default `max_retries = 0` must preserve current fail-fast behavior exactly
- no silent swallowing of errors — every failed attempt is recorded
- retry delay is blocking (no async in this pass)
