## Goal

Enrich durable tool result records beyond flat canonical text.

## Scope

- Define a richer result payload shape
- Record success/failure state, summaries, and relevant output fields
- Keep request/result record relationships explicit

## Behavior

- Tool results carry more than one flattened string
- Durable records preserve enough detail for debugging and later projection
- Flat transcript rendering remains a projection choice rather than the only stored form

## Rules

- Richer payloads should still be stable and testable
- Do not collapse structured result facts into transcript-only text
- Keep result schemas narrow and useful rather than speculative

## Non-Goals

- No full tracing subsystem
- No giant universal result schema for every possible tool shape

## Done When

- `tool_result` records store structured payloads
- At least the built-in tools use that richer payload shape
- Tests prove durable records are richer than transcript-visible result text
