# 665 Shell Intent Streaming Backslide: Buffered Drain Instead of Live Deltas

## Goal
Track and fix a regression where direct shell-intent runs (notably many back-to-back `$ cat ...` lines) do not emit timely live stream deltas, and instead appear as delayed buffered output that is drained later.

## Bug Summary
Observed behavior in `.toas/foo.md` scenario:
- transcript contains many consecutive lines beginning with `$ cat ...`
- run appears quiet for an extended period (repeated subscribe idle timeouts)
- output then appears in chunks (looks streamed) but is likely delayed projection drain of buffered content

This is a backslide from expected live streaming semantics.

## Repro Context
- local host stdio path
- file: `.toas/foo.md`
- input pattern: large burst of consecutive shell intent lines (`$ cat ...`)
- logs showed repeated `push_complete complete=false reason=idle_timeout` before eventual terminal completion and chunked render/apply

## Expected Behavior
- bounded time-to-first-visible-output for long direct shell-intent runs
- incremental deltas should arrive while commands are executing (not only after buffered completion)
- no prolonged idle-timeout loop when meaningful stdout is being produced upstream

## Actual Behavior
- prolonged idle-timeout subscribe churn before first meaningful visible output
- eventual output arrives and is rendered in chunks due to apply-budget path, creating "fake streaming" from buffered backlog

## Scope
In scope:
- identify where shell-intent path loses incremental event emission
- restore true live delta emission semantics for direct user shell-intent bursts
- add regression tests for bounded first-event latency and non-buffered progression

Out of scope:
- unrelated cancel lifecycle behavior
- general model token streaming policy changes

## Done When
- repro scenario no longer exhibits long silent window before first output
- logs show incremental semantic events during command execution
- regression tests cover this pattern and fail on buffered-drain-only behavior

## Related
- `534` local-first async policy/cutover controls
- `664` cancel/pathing progression log (separate but adjacent investigation)
