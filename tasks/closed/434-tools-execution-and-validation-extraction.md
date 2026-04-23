## Goal

Extract the remaining tool-call argument validation and execution boundary logic from `src/toas/tools.py` into focused `tools_cluster` modules so tool orchestration changes are isolated from registry/presentation code.

## Why Now

`tools.py` remains one of the largest and least-covered modules, and the call validation/execution paths are still mixed with unrelated concerns.

## Scope

- move cohesive tool-call validation and execution boundary helpers out of `tools.py`
- keep `tools.py` as thin compatibility facade delegating into extracted helpers
- add direct module tests for extracted execution/validation branches

## Intended Behavior

- tool execution behavior remains unchanged
- validation and execution boundary paths become easier to change and test independently

## Constraints

- preserve existing tool API contracts and error message shapes
- avoid broad behavior changes while extracting seams

## Done When

- `tools.py` sheds a meaningful execution/validation cluster
- extracted helper module has direct branch coverage
- full suite passes
