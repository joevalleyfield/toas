# 340: Runtime prompt-processing progress projection

## Summary
Expose backend prompt-processing/inference progress in TOAS async run streaming so operators can see useful progress signals before generation output lands.

## Problem
For long prompts or cache-miss paths, operators can experience a long silent period before visible output. The `:8080/` human-facing web client demonstrates that prompt-processing progress is already available on the wire, but TOAS currently does not project it.

## Goals
- Surface meaningful prompt-processing progress during async runs.
- Keep progress projection transient and non-disruptive to transcript semantics.
- Support backend-specific telemetry sources without coupling core transcript logic to a single provider.

## Scope
- Identify and integrate the backend wire telemetry surface used by the `:8080/` web client (endpoint or stream) for progress.
  - confirmed wire chunk shape example includes `prompt_progress` with:
    - `total`
    - `processed`
    - `cache`
    - `time_ms`
- Add optional runtime policy toggle(s) for progress projection.
- Project progress into async watch/Vim stream as transient status lines/regions.
  - prompt progress should be replacement-style (single mutable status), not append-only transcript-like flow
  - thinking/content deltas remain append-style
- Ensure final canonical transcript projection remains clean and marker-safe.

## Non-goals (initial pass)
- Perfect cross-provider parity on first implementation.
- Durable storage of high-frequency progress events in transcript message content.
- Log-crawl based parsing for primary progress integration.

## Acceptance Criteria
- During prompt-processing phases, operator sees periodic progress updates before assistant content appears.
- Progress projection is optional and can be toggled without breaking normal runs.
- Final successful output remains canonical TOAS transcript blocks without progress-noise leakage.
- Behavior is tested for at least one concrete backend telemetry source.

## Implementation Notes (Current Pass)
- Added stream callback plumbing for backend `prompt_progress` chunks (`llm.py`).
- Added runtime toggle:
  - `runtime.prompt_progress_mode` (`enabled|disabled`)
  - daemon async path exports `TOAS_STREAM_PROMPT_PROGRESS` accordingly.
- CLI stream path now renders prompt-progress as transient replacement-style status (`\\r...`) and switches back to newline append flow for thinking/content deltas.
- Added tests for:
  - prompt-progress callback extraction from stream chunks
  - daemon env wiring for prompt-progress toggle
  - CLI callback wiring when prompt-progress stream is enabled

## Remaining Risk / Follow-on
- Vim async surface now applies carriage-return replacement semantics during stream accumulation for run regions.
- Optional follow-on: event-level progress rendering if richer provider telemetry (beyond stdout chunk semantics) is needed.

## Status

Closed 2026-04-24.
