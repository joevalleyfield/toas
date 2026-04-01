## Goal

Use prompt assets to shape real generation calls.

## Scope

- Select a generation prompt by version
- Include that prompt in model-facing requests
- Keep generation prompt selection explicit in runtime code

## Behavior

- Generation calls include a system prompt loaded from the prompt library
- Prompt version choice is stable and testable
- Model-facing request assembly remains legible

## Rules

- Generation prompt wiring belongs at the operator boundary
- Prompt selection should not duplicate lineage projection logic
- The first pass should prefer one default generation prompt over many knobs

## Non-Goals

- No per-message prompt mutation layer
- No prompt optimization loop yet

## Done When

- Real generation requests include a loaded generation prompt
- The chosen prompt version is explicit in code and tests
- Prompt changes are reviewable as file diffs
