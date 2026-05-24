# 556: Tool Result User-Scope Marker Projection Gap

## Why

Tool result projection should preserve scope clarity at the transcript frontier.
When an assistant tool call resolves, projected result content without a user scope marker is ambiguous and makes transcript intent boundaries harder to reason about.

## Problem Statement

- Repro path: step an assistant tool-call-frontiered transcript with an allowed tool call.
- Observed: the resulting projection appears without a user scope marker.
- Expected: projected output shape should include the correct user scope marker so tool consequences remain explicit in transcript rendering.
- Confirmed failing surface: Vim plugin streaming lanes on stream completion are not adding the user scope marker.
- Unknown boundary: this may be Vim-streaming-specific or a shared projection omission affecting non-Vim/non-streaming surfaces as well.

## Goals

1. Reproduce the missing-marker behavior with a deterministic fixture.
2. Reproduce and lock down the Vim plugin streaming completion failure path specifically.
3. Identify whether the omission lives in Vim transport/render integration, shared projection shaping, or both.
4. Restore consistent user scope marker projection for allowed assistant tool-call results at least on Vim streaming completion, and across shared surfaces if impacted.
5. Add regression coverage so future projection changes cannot silently drop this marker.

## Non-Goals

- Changing durable record schemas.
- Altering tool authorization policy semantics.
- Broad transcript rendering redesign outside this marker-gap fix.

## Acceptance Criteria

1. A deterministic test fails before the fix and passes after it.
2. Vim streaming-lane completion path reliably renders result output with the expected user scope marker.
3. If shared surfaces are impacted, non-Vim/non-streaming coverage also passes with the same marker expectation.
4. Existing transcript/durable-history invariants remain unchanged.

## Outcome

Closed. Marker handling was normalized for Vim projection formatting and covered with deterministic tests:
- Vim projection unit contract now enforces user-scope bridge + single-blank-line heading spacing for result-leading projection text.
- CLI lane assertions were added to document current streaming/non-streaming and RPC watch marker behavior boundaries.
- Stream-subscribe/session-host push-frame assertion confirms transport preserves result chunks without injecting user scope markers.

Manual validation in live Vim workflow confirmed the corrected spacing behavior and marker appearance expectations for the user’s active editing path.

## Validation

```bash
uv run pytest
```
