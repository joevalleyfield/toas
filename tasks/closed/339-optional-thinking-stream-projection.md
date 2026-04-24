# 339: Optional thinking stream projection

## Summary
Add an optional policy-gated surface to stream model thinking/reasoning deltas during async runs.

## Motivation
Content streaming now works during inference. A follow-up mode should optionally expose reasoning/thinking text as it arrives for backends that provide it.

## Goals
- Keep default behavior unchanged (thinking hidden).
- Add explicit opt-in config for showing thinking stream.
- Preserve transcript/event semantics and avoid accidental persistence leaks.

## Proposed Direction
- Add runtime policy toggle for thinking stream projection.
- Capture `reasoning_content` deltas (when provider emits them) separately from answer text.
- Define projection UX in Vim sentinel/watch output (e.g., labeled section).
- Ensure final assistant content semantics remain deterministic.
- Broaden reasoning extraction shape support for stream chunks:
  - accept alternate reasoning field names (`reasoning`, `thinking`, `reasoning_text`, etc.)
  - inspect nested provider payload surfaces (`model_extra`, `__pydantic_extra__`, `model_dump()`)
  - add opt-in reasoning chunk diagnostics for backend-shape debugging
- Re-enable targeted reasoning request hint in stream mode when thinking callback is active:
  - set `reasoning_format=auto` (without restoring broader legacy request flags)
  - keep default/no-thinking behavior unchanged when thinking stream callback is absent
- Fix stream-mode coherence across execution lanes:
  - runtime `streaming_mode` now drives LLM stream settings in core runtime settings assembly
  - avoids lane-dependent behavior where async env injection streams but sync/fallback silently disables streaming/thinking
- Harden LLM client selection under concurrent daemon requests:
  - protect global OpenAI client cache (`base_url`/api-key keyed) with a lock to avoid cross-thread client swap races

## Acceptance Criteria
- With thinking-stream disabled, behavior matches current shipped streaming.
- With thinking-stream enabled, incremental reasoning content is visible during run.
- Final assistant message content and durable records remain coherent and policy-compliant.

## Progress

- 2026-04-24: Runtime thinking-stream projection path completed.
- Added runtime policy toggle (`runtime.thinking_stream_mode`) with default-hidden behavior and explicit opt-in projection.
- Stream parsing now accepts multiple reasoning field variants and nested payload surfaces (`model_extra`, `__pydantic_extra__`, `model_dump()`).
- Streaming request path now conditionally requests reasoning output (`reasoning_format=auto`) only when reasoning callback is active.
- Streaming-mode coherence and concurrency hardening landed:
  - runtime `streaming_mode` drives stream settings consistently across lanes
  - global OpenAI client cache access is lock-protected for concurrent daemon requests
- Added/expanded tests across LLM/CLI/daemon paths for disabled/enabled thinking-stream behavior and reasoning callback wiring.

## Status

Closed 2026-04-24.
