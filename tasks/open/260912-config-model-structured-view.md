Filed as: 260912-config-model-structured-view
FKA:
AKA: structured config models; human-readable model configuration
Legacy index:

Parent: `260912-config-show-navigation-and-model-view`

keywords: config, models, endpoints, targets, projection, active

# Make filtered model config human-readable by default

## Objective

Replace the dictionary-shaped default for `/config show models` with a compact
structured view while retaining an explicit switch for the exhaustive flat
configuration projection.

## Contract to settle and implement

- `/config show models` presents grouped defaults, endpoints, catalogs, and
  targets for human inspection.
- A clearly named explicit switch exposes the complete legacy flat/dictionary
  projection; preserve its key/value and source semantics during migration.
- The structured view does not silently omit non-deprecated keys: it points to
  the exhaustive view and/or filtered key inspection for fields outside its
  summary.
- Empty/default/unset state is explicit, and secret values never render.

## Acceptance criteria

- Human-readable model output is the default filtered view.
- The explicit flat/dictionary escape hatch is documented and tested.
- Endpoints, known models/catalog observations, targets, and global fallbacks
  are distinguishable in the structured view.
- `--sources` remains meaningful and winning-source semantics are preserved.
- A registry cross-check proves every valid non-deprecated model-related key is
  reachable through structured output, filtered inspection, or the flat view.

## Open decision

Choose and document the switch name (`--flat`, `--dictionary`, or an equivalent
explicit spelling) based on the existing command grammar; do not overload
`--raw`, which already means an endpoint response for `/models`.

## Allowed write surfaces

- config filtered-view rendering and usage/help assets;
- focused unit/acceptance tests;
- this task and generated workboard.

## Status

Ready for implementation.
