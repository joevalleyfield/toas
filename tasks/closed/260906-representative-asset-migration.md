Filed as: 260906-representative-asset-migration
FKA:
AKA: prompt procedure asset slice; common loader migration; asset boundary proof
Legacy index:

Parent: `260905-common-asset-library-migration`
Depends on: `260905-help-assets-runtime-foundation`
Related: `260906-generation-help-facet`; `260906-extraction-help-facet`

keywords: tooling, migration, assets, prompts, procedures, parity, follow-on

Claimed for implementation on 2026-09-06.

## Completion evidence

Migrated representative assets:

```text
src/toas/assets/prompts/shared/schemas/action-lane_v1.txt
src/toas/assets/procedures/search_scope_v1.yaml
```

The prompt loader routes the migrated nested ref through the common packaged
loader while retaining its existing frontmatter/composition path. The
procedure loader routes `search_scope_v1` through the common loader while
retaining defaults, interpolation, YAML validation, and normalized callable
plan shaping. Listings union migrated and legacy families without duplicates.
Package data now includes both YAML and text assets under `assets/`.

Focused prompt/procedure/help result: `111 passed`; Ruff passed. The offline
full run reached `3120 passed, 20 failed, 12 deselected`, with 100% coverage;
the 20 failures are the known sandbox restrictions on socket/HTTP binding and
Vim integration. The pre-package-data full run reached `3140 passed, 12
deselected`; the package-data-only change does not affect runtime semantics.

The remaining prompt and procedure corpus stays in the legacy directories and
continues through the temporary family-loader fallback. No compatibility paths
were removed in this representative slice.

# Representative Prompt and Procedure Asset Migration

## Objective

Prove the common asset boundary with one static prompt and one parameterized
procedure, preserving existing family-specific semantics and public references.

## Representative slice

```text
prompt:    shared/schemas/action-lane_v1
procedure: search_scope_v1
```

The prompt exercises a nested text asset. The procedure exercises YAML parsing,
defaults, parameter interpolation, and normalized callable-plan validation.

## Contract

- The common loader owns packaged resource lookup, safe references, and asset
  identity.
- Prompt loading retains frontmatter/composition/dynamic behavior in
  `prompts.py`.
- Procedure loading retains interpolation, YAML validation, and plan shaping in
  `procedures.py`.
- Existing callers and public refs continue to work during this bounded slice.
- The old package paths remain only as temporary fallback compatibility paths;
  no broad relocation is attempted here.

## Scope

- Add representative files under `src/toas/assets/prompts/` and
  `src/toas/assets/procedures/`.
- Route those two refs through `assets.loader.load_packaged_asset`.
- Keep family-specific fallback behavior for unmigrated assets.
- Make prompt/procedure listing include the migrated refs without duplicates.
- Add parity tests for loaded content, metadata/plan shape, interpolation,
  missing/traversal behavior, and listing.
- Update package data and local migration evidence.

## Non-goals

- Do not migrate the full prompt or procedure corpus.
- Do not remove old directories or compatibility fallbacks yet.
- Do not unify prompt and procedure schemas.
- Do not change prompt composition, procedure execution, or help semantics.

## Acceptance criteria

- The representative prompt loads through the common packaged loader with
  unchanged content and existing public ref behavior.
- `search_scope_v1` loads through the common loader with unchanged defaults,
  interpolation, and normalized plan.
- Listings expose each migrated ref exactly once.
- Traversal and missing-asset protections remain enforced.
- Existing prompt and procedure suites remain parity-safe.

## Allowed write surfaces

- `src/toas/assets/prompts/` and `src/toas/assets/procedures/`;
- narrow common-loader and family-loader seams;
- prompt/procedure tests and package-data declarations;
- this task file and generated `tasks/WORKBOARD.md` sections.

## Required completion evidence

- final representative asset paths and loader ownership;
- before/after parity examples;
- listing and safety test results;
- focused and full required test results;
- explicit inventory of unmigrated families and remaining compatibility paths.
