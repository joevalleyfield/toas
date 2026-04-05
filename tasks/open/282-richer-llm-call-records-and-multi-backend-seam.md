## Goal

Enrich `llm_call` records with latency and token metadata where available, and establish a clean seam for adding a second backend shape without requiring a full rewrite.

## Why Now

Current `llm_call` records capture requested model, returned model, content, and reasoning content — but not latency or token usage. These are useful for performance inspection and cost awareness. The multi-backend seam is a prerequisite for any future work involving a non-OpenAI-compatible endpoint.

## Scope

**Richer records:**
- add `duration_ms: int | None` to `llm_call` payload — wall time from request to first response
- add `usage: dict | None` — token counts as returned by the backend (`prompt_tokens`, `completion_tokens`, `total_tokens`), or `None` if not provided
- update `write_llm_call_record` to accept and persist these fields
- update `generate_assistant_message` to measure and return duration; extract usage from the response object where present
- update `summarize_event` in `graph.py` to include duration and token summary in history output when present

**Multi-backend seam:**
- extract the backend interaction in `llm.py` behind a narrow interface: `def call_backend(messages, settings, extra_body) -> BackendResponse`
- `BackendResponse` is a typed dataclass: `content`, `reasoning_content`, `model`, `usage`, `duration_ms`
- the current OpenAI client path implements this interface
- the interface is the documented extension point for a second backend shape; no second backend is implemented here
- add a brief comment block at the interface definition pointing to what a second implementation would need to provide

## Intended Inputs

- `generate_assistant_message` and `Settings` in `llm.py`
- `write_llm_call_record` and `summarize_event` in `graph.py`

## Intended Outputs

- `llm_call` records with `duration_ms` and `usage` fields (nullable)
- `BackendResponse` dataclass and `call_backend` interface in `llm.py`
- updated `summarize_event` output
- tests covering: duration is non-None on success, usage is passed through when present, `None` is safe when backend omits it

## Constraints

- `duration_ms` and `usage` are optional in the record schema — old records without them remain valid
- no behavioral change to generation; richer records only
- `call_backend` interface must be internal to `llm.py`; callers do not see it change

## Non-Goals

- no second backend implementation in this pass
- no streaming (separate concern, tracked in section 5 notes)
- no cost calculation or token budget enforcement
