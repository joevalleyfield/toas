## Goal

Extend the operator-command surface with a second wave of mechanical commands focused on frontier command adoption, compaction, and outlining.

## Why Now

- `/extract` currently exists but is shaped around historical scan/replay semantics that do not match primary operator intent
- `OperatorConfig` provides the policy persistence layer needed to vary extraction behavior explicitly
- the operator-command substrate (durable records, command result projection) is ready for second-wave commands
- operator pressure is increasingly in mechanical workflows, not just frontier resolution

## Scope

- `275`: pivot `/extract` to frontier-assistant adoption semantics
- `276`: separate historical replay into an explicitly named command
- `273`: `/compact` command — collapse verbose RESULT blocks in the projected transcript to reduce working size
- `274`: `/outline` command — produce a structured topic outline of the current transcript; informational, no mutation

## Intended Inputs

- current `/extract` behavior from `234`, `271`, and `272`
- `OperatorConfig` and `ExtractionPolicy` from `250`
- operator-command record model from `231`/`232`

## Intended Outputs

- `/extract` that is explicitly frontier-focused and operator-aligned
- optional historical replay capability under a separate command name
- two new mechanical commands (`/compact`, `/outline`) with clear invariants
- tests covering each command's normal path, edge cases, and failure modes

## Constraints

- `/extract` must not scan historical transcript by default
- historical replay, if kept, must not hide behind `/extract`
- compaction must be non-destructive to durable history — transcript-level only
- outlining must be purely informational; no writes to history
- all commands follow the existing durable-record pattern

## Done When

- `275`, `276`, `273`, and `274` are closed
- `/extract` behavior matches frontier-assistant adoption intent
- `/compact` and `/outline` are usable and tested
