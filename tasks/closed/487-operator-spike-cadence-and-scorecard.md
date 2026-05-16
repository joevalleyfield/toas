# 487 Operator Spike Cadence and Scorecard

## Objective
Define a lightweight recurring cadence for operator spikes and a consistent scorecard so exploratory drift/protocol signals are captured without blocking acceptance-task closure.

## Why
Spikes are producing useful product signals, but currently mix with acceptance proof and ad hoc interpretation. A recurring structure keeps signal quality high while preserving task boundaries.

## Scope
In scope:
- define cadence trigger (for example weekly or per major runtime/prompt lane change)
- define scorecard fields (success, failure boundary, recovery effectiveness, operator load, drift mode, actionable follow-ons)
- define artifact naming/storage conventions for spike transcripts and notes

Out of scope:
- mandatory runtime behavior changes
- replacing acceptance scenarios

## Deliverables
- documented cadence and scorecard template (docs/acceptance/spikes)
- task references for where to open follow-ons from spike findings

## Done When
- a clear repeatable cadence exists
- scorecard template is documented and used at least once
- spikes can feed roadmap/tasks without reopening 469 by default

## Related
- 469 functional acceptance epic
- 486 runbook vs acceptance boundary cleanup

## Closure
Converted to recurring lane/template on 2026-05-16 under `tasks/recurring/templates` with bootstrap run artifact under `tasks/recurring/runs`.
