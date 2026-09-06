Filed as: 260906-dynamic-capability-asset-migration
FKA:
AKA: capability template asset migration; dynamic prompt asset slice
Legacy index:

Parent: `260905-common-asset-library-migration`
Depends on: `260906-procedure-legacy-removal`

keywords: tooling, migration, active, compatibility, prompts, dynamic, parity

# Dynamic Capability Asset Migration

## Objective

Move the three file-backed dynamic capability templates into the common prompt
asset layout and route their renderer through the common asset loader.

## Scope

- Migrate `overview_v1`, `repo-work_v1`, and `start-here_v1` under
  `src/toas/assets/prompts/dynamic/capabilities/`.
- Preserve frontmatter stripping and runtime template formatting.
- Remove only the old dynamic capability files from `src/toas/prompts/`.
- Keep the remaining prompt corpus and its compatibility fallback unchanged.
- Update loader tests to exercise the common asset seam.

## Acceptance criteria

- All three capability renderers produce their existing output.
- The renderer loads through `assets.loader.load_packaged_asset`.
- Prompt listing and dynamic prompt metadata remain unchanged.
- No runtime capability loader references the old prompt directory.
- Focused tests and lint pass; full-suite results are recorded here.

## Completion evidence

Migrated all three dynamic capability templates:

- `src/toas/assets/prompts/dynamic/capabilities/overview_v1.txt`
- `src/toas/assets/prompts/dynamic/capabilities/repo-work_v1.txt`
- `src/toas/assets/prompts/dynamic/capabilities/start-here_v1.txt`

`capability_prompts._load_template` now uses the common packaged asset loader.
Frontmatter stripping and runtime formatting remain unchanged. The three old
files under `src/toas/prompts/dynamic/capabilities/` were removed; the broader
prompt corpus and its legacy fallback remain in place.

Focused prompt/CLI/operator result: `375 passed`; Ruff passed. The offline full
run reached `3123 passed, 20 failed, 12 deselected`, with 100% coverage. The 20
failures are the known sandbox restrictions on socket/HTTP binding and Vim
integration; no dynamic capability migration failures occurred.
