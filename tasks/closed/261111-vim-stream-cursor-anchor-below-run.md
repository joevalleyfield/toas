Filed as: 261111-vim-stream-cursor-anchor-below-run
FKA:
AKA: vim stream cursor anchor; TOAS:RUN cursor drift; streaming cursor below run region
Legacy index:

keywords: tooling, hardening, active, correctness, usability, vim, stream, transcript, frontier

## Summary

When streaming content into a `## TOAS:RUN` / `## /TOAS:RUN` region, the
cursor should maintain its relative position to the text **below** the run
region. Currently, when the cursor is at or below `## /TOAS:RUN`, each
streamed newline causes the cursor to drift upward by one line relative to
the surrounding text, because the absolute line number is preserved while
content above shifts down.

## Reproduction

1. Open a transcript in the TOAS Vim plugin.
2. Start a step that produces streaming output (e.g. a long LLM response
   with tool calls).
3. Place the cursor on or below the `## /TOAS:RUN` end marker.
4. Observe: as newlines are streamed into the run region, the cursor stays
   on the same absolute line number, but the text it was on moves down,
   so the cursor effectively moves up one line per streamed newline.

## Implementation

Vim stores the saved cursor line in `winsaveview().lnum`. The region
replacement adjusts the cursor line and viewport independently when the
lines they refer to move. The closing marker tracks the end of the region
while it is retained. Text below the region keeps its position through both
streaming updates and final replacement.

Manual `ToasWatch` output follows the end of the buffer when the cursor is
already on the last line. Otherwise, appending output preserves the cursor.

## Verification

The Vim integration test starts a real timer-driven `ToasStep` with staged
transport responses. It checks the cursor's text and column below the run
during growth and after finalization, and checks the closing marker during
growth. The same test exercises manual `ToasWatch` with the cursor away from
and at the end of the buffer.

When inference succeeds and removes the closing marker, a cursor on that
marker lands on the last nonblank line of the finalized output. The Vim regression
covers completion with the cursor on the closing marker and below it,
including a final response delivered as an authoritative projection.
