# 500 Runtime Prompt Workspace Intent/Lens Decomposition Second Pass

## Objective
Decompose `src/toas/runtime/operator_command_prompt_workspace.py` hotspots (`_handle_intent`, `_handle_lens`) into smaller focused helpers with explicit boundaries.

## Why
Current AST rerank shows `_handle_intent` (~132 lines) and `_handle_lens` (~98 lines) as top remaining runtime command hotspots after 498/499 closure.

## Scope
- split `_handle_intent` into focused helpers by sub-flow (parse, validate, mutate, render)
- split `_handle_lens` remaining branch clusters similarly
- keep command behavior and output contracts unchanged
- add direct helper tests for extracted seams

## Done When
- `_handle_intent` and `_handle_lens` are materially slimmer and delegate cohesive helpers
- targeted runtime operator-command tests and full suite pass

## Related
- `400` decomposition umbrella
- `498` closed runtime frontier consequence split
