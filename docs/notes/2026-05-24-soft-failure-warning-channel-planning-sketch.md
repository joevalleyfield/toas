# 2026-05-24 Soft-Failure Warning Channel Planning Sketch

## Purpose

Capture speculative planning for warning-channel/UI behavior without treating it as executed task output.

## Context

Streaming salvage currently preserves useful content on parse/stream failures, but warning visibility and status-line behavior can still be inconsistent across plugin/UI surfaces.

## Event Contract Sketch

- Event name: `warning` (projected, non-durable), with optional subtype `llm_warning` for stream/salvage-origin warnings.
- Lane: diagnostics/status lane only; never assistant content lane.
- Proposed shape:
  - `type`: `warning`
  - `payload.message`: operator-facing warning text
  - `payload.source`: `stream_parse` | `stream_transport` | `fallback_stream` | `plugin_watch`
  - `payload.run_id`: optional async run correlation
  - `payload.severity`: `info` | `warning`
- Semantics:
  - warning frames are additive diagnostics, not terminal outcome changes by themselves
  - warning overlays may co-exist with terminal success ("success with warning" UI treatment) without durable status enum churn

## Plugin Behavior Checklist

- Render warning text in diagnostics/status surfaces only.
- Keep assistant transcript content free from warning prose injection.
- Keep status-line teardown deterministic when terminal status is reached, including warning/salvage paths.
- Preserve current terminality contract (`succeeded`/`failed`/`cancelled`) and treat warnings as overlay metadata.
- Ensure watch/follow fallback paths can emit warning diagnostics without breaking chunk/progress cadence.
- Add/retain tests for warning visibility and non-injection into assistant content.

## Follow-on Slices (Only If Reprioritized)

- protocol warning-frame emission wiring
- Vim/UI warning-channel rendering and status overlay behavior
- regression tests for warning-only overlay semantics
