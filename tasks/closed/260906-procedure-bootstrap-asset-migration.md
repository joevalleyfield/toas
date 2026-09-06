Filed as: 260906-procedure-bootstrap-asset-migration
FKA:
AKA: procedure bootstrap asset slice; repo discovery asset migration
Legacy index:

Parent: `260905-common-asset-library-migration`
Depends on: `260906-representative-asset-migration`

keywords: tooling, migration, active, compatibility, prompts, procedures, parity

# Procedure Bootstrap Asset Migration

## Objective

Migrate the `repo_discovery_triage_v1` procedure and the
`direct/protocol/procedure-bootstrap_v1` prompt into the common packaged asset
layout without changing their content, lookup behavior, or procedure plan.

## Scope

- Add the procedure and prompt under `src/toas/assets/`.
- Route both references through the common asset loader.
- Keep prompt metadata and procedure normalization/interpolation owned by their
  existing family loaders.
- Ensure listings contain each migrated reference exactly once.
- Preserve the old package paths as temporary fallbacks for this bounded slice.
- Add focused parity tests and record verification evidence here.

## Acceptance criteria

- Both migrated assets load successfully from the common packaged layout.
- The procedure produces the same normalized four-step plan as before.
- The prompt retains its frontmatter metadata and procedure reference.
- Prompt and procedure listings do not duplicate migrated entries.
- Focused tests and lint pass.

## Completion evidence

Migrated assets:

- `src/toas/assets/procedures/repo_discovery_triage_v1.yaml`
- `src/toas/assets/prompts/direct/protocol/procedure-bootstrap_v1.txt`

Both family loaders now route these references through the common packaged
asset loader. Prompt frontmatter parsing and procedure plan normalization remain
owned by their existing loaders. Listings union the migrated and legacy trees
without duplicate references, and the old files remain temporary fallbacks.

Focused prompt/procedure/help result: `113 passed`; Ruff passed. The offline
full run reached `3122 passed, 20 failed, 12 deselected`, with 100% coverage;
the 20 failures are the known sandbox restrictions on socket/HTTP binding and
Vim integration. No migration-specific failures occurred.
