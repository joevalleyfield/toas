## Goal

Plan a low-priority follow-up to improve plugin/UI handling of soft stream failures and warning-channel diagnostics.

## Status Note

Closed as planning deliverable. Implementation remains deferred unless reprioritized.

## Why Now

Streaming salvage now preserves useful output on parse/stream failures, but plugin status-line cleanup and warning visibility can still feel inconsistent.

## Scope

- define warning side-channel event shape for soft failures/salvage (for example `llm_warning`)
- define plugin status-line cleanup behavior when run completes via salvage path
- identify UX labeling options (`succeeded_with_warning` style, UI-only)
- keep assistant content lane free of warning noise

## Intended Behavior

- warnings are visible in plugin diagnostics/status lanes, not injected into assistant content
- status-line teardown is deterministic for soft-failure/salvage completions
- operator can distinguish clean success vs success-with-warning in UI surfaces

## Constraints

- low priority / follow-up only
- no durable status semantic churn unless explicitly approved
- preserve existing transcript and events compatibility where possible

## Done When

- event contract sketch and plugin behavior checklist are documented
- implementation slices are broken out into concrete tasks (if still desired)

## Priority

- explicitly deferred; not currently prioritized

## Planning Reference

- Speculative planning material is captured in:
  - `docs/notes/2026-05-24-soft-failure-warning-channel-planning-sketch.md`

## Progress

- 2026-05-24: planning sketch drafted in docs/notes for future reprioritization.
- 2026-05-24: task closed after documenting planning product and implementation slice sketch; no implementation executed in this task.
