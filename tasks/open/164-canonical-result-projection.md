## Goal

Project transcript-visible `RESULT` blocks from richer structured tool outputs.

## Scope

- Derive canonical result text from structured tool results
- Keep transcript rendering separate from stored result payloads
- Make result projection consistent across built-in tools

## Behavior

- Users still receive readable `RESULT` blocks on stdout
- Those blocks are rendered from richer durable tool facts
- Different tools can share a stable projection contract without identical raw payloads

## Rules

- Transcript-visible results are projections, not the source of truth
- Projection logic should live at a boundary layer, not inside storage primitives
- Canonical text should be predictable enough to test

## Non-Goals

- No rich UI rendering layer
- No requirement that every tool have the same exact textual format

## Done When

- `RESULT` text is derived from structured tool records
- The projection contract is consistent and test-covered
- The transcript stays readable while the durable records get richer
