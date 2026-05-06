# 479 Stdin And One-Shot Control CLI Step Input With Durable Effects

## Goal

Add a CLI input path that can run one `step` consequence without staging transcript edits into a session file first, while preserving normal durable event semantics.

## Why

Simple control operations (for example `/session show`) currently require file-staging overhead. This creates avoidable operator friction and a catch-22 when trying to inspect/adjust session-file targeting.

## Scope

- add a stdin-driven `step` mode (for example `toas step --stdin`) that reads transcript fragment input from stdin
- optionally add a one-shot control command form (for example `toas step --control "<slash command>"` or equivalent)
- preserve append-only durability to event log (`.toas/events.jsonl` default)
- preserve normal consequence and side-effect behavior (`command_*`, `config_override`, tool/model records, queue state, etc.)
- keep existing transcript-file workflow unchanged as default behavior

## Non-Goals

- no change to durable-history model or record taxonomy
- no hidden autonomous loop behavior
- no mandatory migration away from transcript-file-first workflows

## Done When

- operator can run control-lane equivalent command(s) without first editing session file
- stdin/control-shot modes still write durable records/events and apply durable effects
- stdout contract remains clear and deterministic for one-step consequence output
- transcript-file mode remains backward-compatible
- tests cover:
  - stdin input resolution path
  - one-shot control command path (if included)
  - durable side effects (including config override records)
  - no-regression for existing `toas step` file-based behavior

## Initial Slices

1. CLI shape + UX contract (`--stdin` and optional `--control`)
2. runtime plumbing into existing `step` consequence path
3. durable side-effect parity tests
4. docs/help updates and examples

## Status

Closed.

Implemented:
- `toas step --stdin` reads transcript fragment from stdin and appends it to the working transcript for one-step consequence resolution.
- `toas step --control "<slash command>"` injects a real `TOAS:CONTROL` turn for one-step consequence resolution.
- default `toas step` behavior remains unchanged.
- path preserves normal durable event/effect semantics by running through the existing local step pipeline.

Verification:
- `uv run pytest` (full suite) passed with coverage gate satisfied.
