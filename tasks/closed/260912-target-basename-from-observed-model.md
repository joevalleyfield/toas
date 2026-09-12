Filed as: 260912-target-basename-from-observed-model
FKA:
AKA: short target names; path-like model target promotion
Legacy index:

Parent: `260912-model-observation-raw-details`
Related: `260912-models-single-endpoint-default`

keywords: models, targets, config, naming, implementation, active

# Use concise target IDs for path-like observed models

## Objective

Make automatic target promotion use the agreed basename display identity for
path-like model IDs, while keeping the raw model ID in the target's `model`
field so invocation remains correct.

## Contract

- A model ID such as `/models/Qwen/model.gguf` promotes to a target ID based on
  `model.gguf`, not the full path.
- The target's stored model value remains the raw endpoint model ID.
- Existing non-path model IDs and explicit target authoring remain unchanged.

## Acceptance criteria

- `/config target add --all-known ENDPOINT` creates concise target IDs for
  path-like known model IDs.
- Target listing shows the concise target ID and the raw model value.
- Selection and invocation continue to use the raw model ID.
- Collisions remain deterministic and are not silently overwritten.

## Allowed write surfaces

- target ID derivation and promotion;
- focused unit/acceptance tests;
- this task and generated workboard.

## Completion evidence

Target ID derivation now uses the basename of path-like model IDs, so
`/models/Qwen/model.gguf` promotes to `local-llama-model.gguf` while the target
continues to store and invoke the raw model ID. Existing explicit and
non-path model forms remain unchanged; collisions continue through the
existing deterministic skip behavior.

Focused result: `165 passed` across target and operator tests.
Full result: `3231 passed, 17 deselected`; coverage `100%`; acceptance and
integration `17 passed`; Ruff and mypy passed.

## Status

Closed 2026-09-12.
