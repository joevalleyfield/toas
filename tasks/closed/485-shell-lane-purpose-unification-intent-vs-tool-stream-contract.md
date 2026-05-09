## Goal

Unify shell-lane purpose across user-intent (`$ ...`) and model-callable (`shell`/`shell_script`) paths so runtime output behavior is intentionally aligned while policy and UX divergences remain explicit.

## Why

We need compare-and-contrast, not forced sameness. Current behavior drifts by lane in ways that are hard to reason about during live operator use. Divergence should be intentional and documented; accidental divergence should be removed.

## Scope

- Define one shared runtime stream/projection contract for shell execution outcomes.
- Preserve intentional lane differences:
  - bounded policy only for model-callable lane
  - user-intent lane remains unbounded
  - invocation/provenance remain distinct.
- Implement minimal runtime changes so both lanes provide equivalent live progress semantics during async watch.
- Add tests that assert parity where intended and difference where intended.

## Non-Goals

- Making both lanes identical in argument syntax, policy checks, or help text.
- Replacing existing durable record shapes.
- Redesigning tool schema.

## Contract

1. Shared behavior:
   - long-running shell execution emits incremental stream progression visible to watch clients.
   - `watch` semantics remain protocol-based (`poll` snapshot, `follow` progression wait).
   - terminal result projection remains replay-safe.

2. Intentional differences:
   - model-callable lane enforces shell grants/workspace bounds.
   - user-intent lane bypasses those bounds by design.
   - provenance indicates lane origin.

## Done When

- [x] Both lanes show incremental mid-run visibility under Vim/daemon watch for the same slow-output shape.
- [x] Policy divergence remains intact and covered by tests.
- [x] Docs clarify purpose unification and intentional divergence boundaries.

## Implementation Slices

1. Runtime boundary alignment:
   - unify shell stdout streaming behavior at execution path where feasible.
   - ensure user-intent and callable lanes both emit incremental stream progression in async path.

2. Projection behavior:
   - avoid lane-specific silent fallback to terminal-only output for stream-capable commands.

3. Test matrix:
   - daemon/runtime unit tests for lane parity on incremental output progression.
   - explicit tests for preserved policy divergence.
   - Vim/Vader functional parity test using the same slow shell output shape in both lanes.

## Progress

- Landed first runtime alignment slice:
  - user-intent shell execution now explicitly requests stream-capable subprocess behavior,
    independent of ambient env toggles that may differ by invocation path.
- Preserved intentional divergence:
  - policy bounds and callable validation remain lane-specific.
- Verified no regression across core shell/step/daemon tests.
- Added direct tests locking lane intent at execution boundary:
  - user context forces stream-capable subprocess override.
  - assistant/tool context keeps streaming-mode selection policy-driven (no forced override).
- Added shared shell-stream policy resolver with scoped precedence:
  - defaults < env < configured runtime flags
  - transcript `/env` modifiers remain explicit per-step overrides at execution time.
- Wired both user-intent and callable execution paths in step runtime to the same resolved stream flag.
- Added failing-then-passing boundary coverage for slow user `$ ...` shell shorthand under `step_async` + `watch` poll mode.
- Fixed cold async daemon stream reader batching behavior (chunk-fill/EOF bias) by switching to line-driven incremental reads in text mode.
- Added hybrid shell streaming flush policy in subprocess execution path:
  - flush on newline OR byte threshold OR max-latency timeout.
  - reduced burstiness and improved intermediate visibility for long-running output.
- Added explicit divergence coverage:
  - user-intent `$ ...` lane executes unbounded command shape that callable lane rejects under shell grants.
- Added incremental watch progression coverage for user/callable slow-output signatures in run-store poll mode.
- Documented unification boundary in capabilities doc:
  - shared streaming contract, intentional policy divergence, protocol-first watch semantics.

## Related

- `483` command stdout streaming to Vim plugin debug/fix
- `484` watch protocol poll vs follow semantics
