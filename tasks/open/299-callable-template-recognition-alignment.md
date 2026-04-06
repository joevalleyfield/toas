## Goal

Eliminate callable-template mismatch between prompt/entrainment wording and extraction recognition by defining a canonical key contract with explicit backwards-compatible aliases.

## Why Now

Live usage surfaced confusion between template keys such as `tool_name`, `operation`, and `command`. This creates avoidable extraction misses and inconsistent operator expectations.

## Scope

- declare canonical callable key names for command/tool intent
- update prompt/entrainment library material to use canonical shape
- add extractor alias support for legacy spellings (`tool_name`, `operation`) where safe
- add deterministic conflict handling when multiple competing keys are present
- normalize projected/durable output to canonical key naming

## Intended Inputs

- extraction logic in `src/toas/step.py`
- tool invocation semantics in `src/toas/tools.py`
- prompt assets in `src/toas/prompts/...`

## Intended Outputs

- canonical callable template contract (documented)
- compatibility alias map in extraction path
- explicit conflict error text for ambiguous mixed-key payloads
- tests for canonical, alias, and conflict cases

## Constraints

- maintain compatibility with existing transcript history where feasible
- avoid semantic fork between direct user intent lane and model-addressable tool lane
- keep extraction deterministic and mechanical

## Non-Goals

- no fuzzy/LLM-assisted intent guessing
- no expansion of tool registry scope

## Done When

- canonical callable template is documented and used in prompt assets
- alias forms are recognized in extraction tests
- conflicting key forms fail with clear actionable error
- output path normalizes to canonical names
