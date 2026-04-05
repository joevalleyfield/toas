## Goal

Extend the operator-command surface with a second wave of mechanical commands focused on extraction execution, non-tail targeting, compaction, and outlining.

## Why Now

- `/extract --dry-run` is in place; the next natural step is live execution
- `OperatorConfig` provides the policy persistence layer needed to vary extraction behavior explicitly
- the operator-command substrate (durable records, command result projection) is ready for second-wave commands
- operator pressure is increasingly in mechanical workflows, not just frontier resolution

## Scope

- `271`: `/extract` live execution — from dry-run identification to actual execution with durable records
- `272`: non-tail extraction policy — implement `yaml_position = any` and `yaml_position = first` in `_extract_plan` and the `/extract` scan, gated on `OperatorConfig`
- `273`: `/compact` command — collapse verbose RESULT blocks in the projected transcript to reduce working size
- `274`: `/outline` command — produce a structured topic outline of the current transcript; informational, no mutation

## Intended Inputs

- `/extract --dry-run` from `234`
- `OperatorConfig` and `ExtractionPolicy` from `250`
- operator-command record model from `231`/`232`

## Intended Outputs

- live extraction that is durable, attributable, and replay-safe
- config-controlled extraction policy with non-tail path implemented
- two new mechanical commands (`/compact`, `/outline`) with clear invariants
- tests covering each command's normal path, edge cases, and failure modes

## Constraints

- extraction execution must not re-execute messages that already have associated `tool_request` records
- compaction must be non-destructive to durable history — transcript-level only
- outlining must be purely informational; no writes to history
- all commands follow the existing durable-record pattern

## Done When

- `271`–`274` are closed
- extraction can be executed live, not just dry-run
- non-tail extraction is implemented and config-gated
- `/compact` and `/outline` are usable and tested
