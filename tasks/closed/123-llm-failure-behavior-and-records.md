## Goal

Make model-call failures and durable model-call facts explicit.

## Scope

- Define how generation failures surface to the operator
- Add minimal retry policy if justified
- Record model-facing request/response facts durably when they materially aid debugging

## Behavior

- Failures are visible and do not silently degrade into fabricated assistant content
- Retries, if present, are bounded and explicit
- Durable model-call records remain distinct from message events and tool records

## Rules

- Do not hide backend failures inside transcript content
- Keep model-call records narrowly useful rather than exhaustively verbose
- Preserve the split between durable facts and user-visible transcript consequences

## Non-Goals

- No elaborate tracing framework yet
- No caching or deduplication layer yet

## Done When

- Generation failures are explicit enough to debug
- The event log can capture minimal model-call facts when needed
- The runtime behavior is deterministic enough to test without a live backend
