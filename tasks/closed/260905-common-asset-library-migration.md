Filed as: 260905-common-asset-library-migration
FKA:
AKA: shared asset loader; prompts procedures help assets; asset library migration
Legacy index:

Parent: `260901-help-system-design-survey`
Related: `141`; `200`; `358-agentic-low-activation-execution-arc-procedures-and-lane-splits-umbrella`; `482-file-backed-capability-prompt-templates-follow-on-to-471`

keywords: tooling, migration, inception, maintainability, compatibility, assets, prompts, procedures, help

# Common Asset Library Migration

## Objective

Establish a common packaged asset layer for prompts, procedures, and runtime
help, with family-specific loaders and a final layout under `assets/`.

The target is a shared asset foundation, not a universal semantic registry.
Prompts, procedures, and help should retain their own content models,
validation, composition, and runtime behavior while sharing the mechanics that
are genuinely common.

## Motivation

TOAS already has file-backed prompt and procedure assets, while help content is
still substantially hardcoded in source. Help will become a runtime feature
and needs a stable home for curated topics, descriptions, aliases,
relationships, and progressive-disclosure metadata. The existing prompt and
procedure loaders provide useful patterns, but their current directories and
loaders are separate.

## Target shape

```text
src/toas/assets/
  loader.py
  prompts/
  procedures/
  help/
```

The shared layer may own resource lookup, safe references, prefix listing,
common metadata/frontmatter, asset identity, versioning, and static/dynamic
provenance. Family loaders remain responsible for:

- prompt composition and runtime-conditioned rendering;
- procedure interpolation, plan parsing, and callable validation;
- help topic facets, config-key relationships, search, and progressive
  disclosure.

## Migration posture

- Do not relocate assets greedily or create a broad compatibility abstraction
  before a family has a clear contract.
- Move prompt, procedure, and help families in bounded slices.
- Preserve existing public references during each transition only as a
  temporary migration measure.
- The intended final form has assets under `src/toas/assets/` and no remaining
  compatibility adapters for the old package paths.
- Dynamic assets may remain loader-registered rather than file-backed, but
  must use the common asset identity/provenance model where applicable.

## Scope

- Define the common asset contract and resource-loading boundary.
- Introduce the `assets/` package layout without changing asset semantics.
- Migrate existing prompt and procedure loading incrementally.
- Add help assets as a runtime-loadable family, beginning with the curated
  configuration topics and their optional plain-help facets.
- Migrate callers and tests, then retire old directories, loaders, and
  compatibility adapters once no supported references remain.

## Non-goals

- No single schema that makes prompts, procedures, and help interchangeable.
- No immediate exhaustive help catalog.
- No greedy relocation of every asset in one change.
- No change to prompt composition, procedure execution, or help semantics
  merely as a consequence of package layout.

## Acceptance criteria

- A documented common asset boundary exists with explicit family ownership.
- Static assets can be resolved, listed, and identified from the final
  `assets/` layout using safe references.
- Prompt and procedure behavior remains parity-safe during migration.
- Help assets can be loaded at runtime and support metadata needed for curated
  topics, aliases, relationships, and optional facets.
- Existing asset consumers have migrated to the new boundary.
- Old asset directories and compatibility adapters are removed after callers
  and tests no longer depend on them.
- Tests cover missing/invalid assets, traversal rejection, listing, metadata,
  dynamic/static provenance where applicable, and family-specific behavior.
- Completion evidence records each migrated family, removed adapter, and
  prompt/procedure/help parity result.

## Suggested decomposition

1. Define the shared loader/resource contract and final package shape.
2. Migrate one representative prompt and procedure path without semantic
   change.
3. Introduce the help asset family and configuration-topic loader/search.
4. Migrate remaining prompt and procedure families in bounded slices.
5. Remove compatibility paths and verify the final asset-only layout.

The decomposition is a sequencing aid, not a commitment to a single
implementation structure. A child task should be opened when one slice has a
clear owner and test story.

The first bounded child is
`260905-help-assets-runtime-foundation`. It proves runtime help assets and
the minimum shared loading mechanics through the configuration-help vertical
slice; it deliberately does not move prompt or procedure assets yet.

## Required completion evidence

- final asset tree and loader ownership map;
- migration ledger for prompts, procedures, and help families;
- tests demonstrating old-path retirement and final-path behavior;
- explicit confirmation that no compatibility adapter remains;
- recorded parity or intentional-difference notes for dynamic assets.

## Completion Evidence

Closed: the common asset boundary is established at `src/toas/assets/` with
shared safe lookup/listing in `assets/loader.py` and family-owned loaders for
prompts, procedures, and help. The runtime prompt corpus contains 48 asset
files, the procedure family contains 3 assets, and the configuration-help
catalog is packaged under `assets/help/config.yaml`.

Prompt and procedure callers use the common packaged loader; dynamic prompt
renderers remain code-registered while their static templates use the asset
identity/provenance boundary. Help topics, facets, aliases, related keys, and
search metadata load at runtime. The old prompt and procedure trees contain no
runtime assets or compatibility loader; the sole remaining old-path file is a
golden comparison fixture for an existing prompt test.

Verification: prompt, procedure, and help parity tests are covered by the full
strict suite, most recently 3,208 passed, 14 deselected, and 100% coverage;
Ruff passed. Dynamic/static differences are intentional and recorded in the
family-specific migration tasks.
