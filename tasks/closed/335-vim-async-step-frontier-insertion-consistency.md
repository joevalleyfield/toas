## Goal

Fix Vim async step (`<leader>s`) so placeholder insertion and streamed final output are anchored at the evaluated frontier location (tail), not at the current cursor position.

## Why Now

Current `<leader>s` behavior can evaluate frontier-at-tail while inserting output at cursor, creating split semantics that are confusing and can place TOAS output in the wrong region.

## Scope

- reproduce and cover mismatch between:
  - evaluation frontier location
  - async placeholder insertion location
  - streamed completion replacement location
- align async insertion semantics with frontier evaluation semantics
- preserve non-disruptive cursor behavior (no forced jump to end)
- keep `<leader>S` behavior unchanged

## Intended Behavior

- `<leader>s` evaluates at tail/frontier and inserts async placeholder at that same tail/frontier region
- streamed output replaces the matching placeholder at that anchored region
- user cursor/focus can remain where they are unless they explicitly navigate

## Intended Inputs

- Vim plugin async step dispatch and placeholder-anchor logic
- callback/timer completion path that writes final output
- Vim integration tests (or focused regression test harness where available)

## Intended Outputs

- predictable async output placement
- consistent small-s vs big-S operator semantics

## Constraints

- avoid buffer-wide jumps or forced cursor repositioning
- keep async cancel/streaming behavior intact

## Non-Goals

- no redesign of sync `<leader>S` UX
- no broader multi-projection/frontier policy changes

## Done When

- async placeholder and final output both land at frontier-evaluated location
- regression coverage proves cursor-position independence for `<leader>s`
- manual smoke confirms `<leader>S` remains unchanged
