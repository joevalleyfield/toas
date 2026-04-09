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
- Add optional runtime policy toggle(s) for progress projection.
- Project progress into async watch/Vim stream as transient status lines/regions.
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
