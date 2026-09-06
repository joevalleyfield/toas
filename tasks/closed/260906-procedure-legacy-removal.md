Filed as: 260906-procedure-legacy-removal
FKA:
AKA: procedure asset-only loader; retire legacy procedure directory
Legacy index:

Parent: `260905-common-asset-library-migration`
Depends on: `260906-procedure-bootstrap-asset-migration`

keywords: tooling, migration, active, compatibility, procedures, parity

# Procedure Legacy Removal

## Objective

Complete the procedure-family migration by moving the final procedure into the
common packaged asset layout and removing the legacy procedure directory and
loader fallback.

## Scope

- Add `task_pick_first_action_v1` under `src/toas/assets/procedures/`.
- Make `toas.procedures` list and load only through the common asset loader.
- Preserve missing-asset errors, interpolation, YAML validation, and normalized
  callable-plan behavior.
- Remove the old `src/toas/procedures/` assets and package-data entry.
- Update tests to exercise the new loader seam.

## Acceptance criteria

- All three procedures load from `assets/procedures/`.
- The final migrated procedure is byte-identical to its former source.
- No runtime procedure code references the old package directory.
- Procedure listings and missing/invalid asset behavior remain covered.
- Focused tests and lint pass; full-suite results are recorded here.

## Completion evidence

Migrated the final procedure:

`src/toas/assets/procedures/task_pick_first_action_v1.yaml`

The three procedure assets are byte-identical to their former files. The
procedure family loader now lists and loads exclusively through the common
packaged asset loader, while preserving its missing-asset compatibility error,
interpolation, YAML validation, and normalized callable-plan behavior.

Removed the legacy `src/toas/procedures/` directory and its
`procedures/**/*.yaml` package-data entry. No runtime procedure code references
the old directory; historical task notes are the only remaining textual
references.

Focused procedure/tool/help result: `176 passed`; Ruff passed. The offline full
run reached `3123 passed, 20 failed, 12 deselected`, with 100% coverage. The 20
failures are the known sandbox restrictions on socket/HTTP binding and Vim
integration; no procedure migration failures occurred.
