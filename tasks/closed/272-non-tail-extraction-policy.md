## Goal

Implement the `yaml_position` config knob so extraction is no longer locked to the last YAML block in a message — operators can opt into scanning all blocks or preferring the first.

## Why Now

`extraction.yaml_position` exists in `OperatorConfig` and is wired through `step()`, but the `any` and `first` paths are not implemented — the config key is plumbing without behavior. This task adds the behavior.

## Scope

- implement `yaml_position = "any"` in `_extract_plan` (step.py and graph.py):
  - parse all YAML blocks in the message, not just the last
  - return the first block that validates as a tool plan
  - if multiple blocks validate, treat as ambiguous and return `None` (let operator use `--index` to resolve)
- implement `yaml_position = "first"` as a strict first-block-only variant
- `yaml_position = "tail"` remains the default and current behavior
- update the `/extract` dry-run and execute scan to use config-driven extraction per message
- update `extract_plan` in `graph.py` to accept an optional position parameter (or use a shared helper) so the live-step path and the CLI record path stay consistent
- document the ambiguity behavior in the command error output

## Intended Inputs

- `OperatorConfig.extraction.yaml_position` from `250`
- `_extract_plan` and `_extract_yaml_tail_block` in `step.py`
- `extract_plan` in `graph.py`
- `/extract` command from `234`/`271`

## Intended Outputs

- `yaml_position` knob produces observable behavioral difference
- ambiguity when multiple valid blocks exist is reported explicitly, not silently resolved
- tests covering:
  - `tail` selects last block (current behavior, unchanged)
  - `first` selects first block
  - `any` selects first valid plan block
  - `any` with multiple valid blocks returns `None` (ambiguous)
  - config propagated correctly through `/extract` scan

## Constraints

- tail behavior must remain identical to current at default config
- no silent tie-breaking — ambiguity is surfaced, not resolved by position alone
- graph.py and step.py must not have diverged extraction logic after this lands (the duplication noted earlier should be resolved here or explicitly tracked)

## Note On Duplication

`extract_plan` in `graph.py` and `_extract_plan` in `step.py` are near-identical. This task is a good opportunity to consolidate them or at minimum make them share the position-aware core. If consolidation adds meaningful scope, it can be deferred to a QoL task, but the gap should not widen.
