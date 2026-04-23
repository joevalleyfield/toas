## Goal

Extract capability-help/profile rendering and tool-shape presentation helpers from `src/toas/tools.py` into a focused module.

## Why Now

Capability/help rendering paths are high-churn prompt-surface logic and are currently entangled with tool registry and execution code in `tools.py`.

## Scope

- move capability/help/topic rendering helpers and related shape-formatting logic out of `tools.py`
- keep `tools.py` as dispatch facade with compatibility wrappers as needed
- add direct tests for rendering/profile branch behavior in the extracted module

## Intended Behavior

- user-facing help and capability output remains stable
- rendering logic becomes isolated and easier to iterate without touching execution paths

## Constraints

- maintain current textual contract/style for existing help surfaces unless explicitly changed
- avoid mixing this slice with unrelated execution refactors

## Done When

- rendering/help cluster is extracted from `tools.py`
- branch-heavy rendering behavior is directly tested
- full suite passes
