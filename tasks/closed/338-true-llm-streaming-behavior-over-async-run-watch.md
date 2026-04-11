# 338: True LLM streaming behavior over async run/watch

## Summary
Align async streaming behavior with user expectations by streaming generation deltas during inference (not only post-completion stdout chunks).

## Problem
Current async/watch flow streams subprocess stdout from `toas step`, but LLM generation is currently non-streaming request/response. This makes long-running inference appear idle until completion.

## Scope
- Clarify and document current behavior vs target behavior.
- Add real incremental generation streaming for supported backends.
- Preserve existing transcript/event invariants while introducing progressive UI updates.

## Proposed Direction
- Add streaming-capable LLM path in `llm.py` (provider permitting).
- Thread delta callback hooks through generation path to async runtime.
- Improve daemon stream ingestion for non-line-delimited deltas.
- Keep thinking/reasoning projection policy-gated.

## Acceptance Criteria
- During long inference, async watch returns incremental content updates before final completion.
- Vim nonblocking sentinel updates progressively during generation.
- Final transcript projection remains coherent and deterministic.
- Existing non-streaming fallback path remains available when backend/provider does not support streaming.
