## Goal

Ensure command stdout streaming is visible in the Vim plugin during TOAS runs, with parity across direct CLI, daemon/RPC, and plugin transport paths.

## Why Now

Interactive operator use depends on seeing progress and tool/command output as it happens. Missing streaming in Vim makes long steps opaque and weakens trust in runtime behavior.

## Scope

- Reproduce and isolate where stdout streaming is lost along the chain:
  - runtime emission
  - daemon async event capture/store
  - RPC transport payloads
  - Vim client consumption/render
- Add targeted tests at each boundary to prove behavior and prevent regression.
- Implement the smallest fix that restores streaming without changing durable-history semantics.

## Non-Goals

- Redesigning event schemas beyond what is required for streaming parity.
- Broader UX redesign of Vim presentation formatting.

## Done When

- Repro exists and is deterministic.
- Root cause is identified at a specific boundary (or boundaries).
- Streaming stdout is observable in Vim during command execution.
- Tests cover the failing boundary and pass across:
  - direct/local path
  - daemon/RPC path
  - Vim client integration boundary (mocked where needed).
- Docs/runbook notes include troubleshooting checkpoints for this class of issue.

## Initial Debug Plan

1. Establish baseline matrix:
   - `toas step` local path (no daemon)
   - `toas step` via daemon/RPC
   - Vim plugin invocation
2. Instrument/observe emitted event types and payload contents at each hop.
3. Verify whether stdout is:
   - never emitted,
   - emitted but not transported,
   - transported but not rendered.
4. Apply minimal fix at the first broken boundary; avoid duplicate fallback logic.
5. Backfill tests and short operator troubleshooting notes.

## Constraints

- Preserve existing durable record invariants.
- Keep CLI-thin direction intact (`470` alignment).
- Prefer belt-or-suspenders reduction: no redundant compensating branches unless proven necessary.

## Related

- `470` operator API seam and CLI-thin wrapper migration
- `469` functional acceptance epic
- `463` session identity/buffer mapping (possible Vim-side interaction)
