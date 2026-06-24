Filed as: 260623-host-stdio-llm-failure-surfacing
FKA:
AKA: host-stdio failed-run cause visibility; async llm error surfacing; visible backend error line
Legacy index:

keywords: runtime, hardening, active, usability, async, host-stdio, stream, failure, surfacing

# Host-stdio LLM Failure Surfacing

Parent: `260614-architecture-follow-through-coordination`
Related: `260614-model-backend-failure-handoff`; `260623-host-stdio-llm-error-surfacing-probe`

## Current Reality

Host-stdio is supposed to append a compact visible cause line for failed runs,
but we have current evidence that an LLM/provider failure can end up durable in
`llm_call` history without becoming operator-visible in the host-stdio
run/watch surface.

## Desired Reality

When a host-stdio run fails because model invocation fails, the operator sees a
compact visible failure cause in the surfaced run output without needing to
inspect `events.jsonl` or history records manually.

## Scope

- Trace the current host-stdio async failure path from model invocation failure
  through run-store/watch/push rendering.
- Identify where the failure cause is dropped, suppressed, or not rendered.
- Restore the visible failed-run cause behavior for this path without changing
  backend lifecycle ownership semantics.

## Non-Goals

- Designing automatic backend recovery or restart behavior.
- Reclassifying provider failure as backend lifecycle failure.
- Broadening the task into a general backend-handoff architecture rewrite.

## Known Facts

- Local sync `step` still raises a visible `SystemExit` on generation failure.
- The host-stdio path has a closed UX task claiming failed runs append a compact
  visible cause line, so this is either a regression or an uncovered path.
- The child repro-probe task exists specifically to make this failure path
  easy to trigger end to end without depending on accidental backend quirks.

## Acceptance

- A host-stdio end-to-end test demonstrates that a forced LLM request-shape
  failure produces an operator-visible failure cause line.
- The visible failure cause does not require reading durable `llm_call`
  records manually.
- Default happy-path host-stdio streaming behavior remains unchanged.

## Completed

- Reproduced the bug end to end under host-stdio and pinned it with an
  integration test that forces model-invocation failure through the real async
  host path.
- Fixed the local async worker so `SystemExit` from the sync step path becomes
  a failed terminal run instead of silently leaving the run stuck at
  `running`.
- Fixed host push completion so `push_complete` preserves terminal error detail
  alongside `status=failed`, matching the failure text already available in
  watch payloads and terminal error events.
- Added focused bridge and worker coverage for the failure-finalization and
  terminal-error propagation seams.
