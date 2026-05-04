# 476 Inert Wrapping Policy For Result Projections And Restep Safety

## Objective
Define and implement deterministic inert-wrapping behavior for projected `RESULT` content that can be reinterpreted as executable slash/frontier intent on subsequent steps.

## Why
Recent runbook spikes showed a failure mode where raw result lines (especially slash-prefixed or command-like/path-like lines) were replayed as live commands after restep, causing cascades of `unknown command` errors and derailing implementation loops.

## Scope
In scope:
- Define exact trigger conditions for when result content should be wrapped inert before becoming part of next-step transcript context.
- Implement wrapping behavior at the projection boundary (not ad-hoc in operator prompts).
- Preserve readability while preventing accidental command re-trigger.
- Add tests covering both positive wrapping cases and non-wrapping normal cases.

Out of scope:
- Broad rewrite of command parsing semantics.
- Aggressive blanket inert wrapping of all results.
- Changes to durable history model beyond projection safety behavior.

## Candidate Trigger Conditions (Initial)
Wrap projected result payload inert when any of the following are present at line start in non-code-fenced result text:
- slash-command-like lines (e.g., `/help`, `/config ...`, `/path/...`)
- user-shell shorthand markers that could arm execution (`$ ...`)
- emitted lines that match known command route patterns in `SLASH_COMMANDS`

Do not wrap when:
- content is already inside explicit inert markers/fences
- content is compact/summary-only and contains no executable-looking lines
- wrapping would hide short safe status summaries that need immediate readability

## Acceptance Criteria
- Restep of transcripts with wrapped result content no longer triggers unintended operator command execution.
- Existing intentional slash command flows remain unaffected.
- Tests prove:
  - wrapping occurs when risky patterns appear,
  - wrapping does not occur for safe summaries,
  - no regressions in expected projection/readability paths.

## Related
- `469` functional acceptance epic
- `470` operator API seam and CLI-thin migration
- `465` control-lane projection semantics

## Tracking
- Status: closed
- Opened: 2026-05-04
- Closed: 2026-05-04
- Owner: codex+operator pairing
