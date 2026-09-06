Filed as: 260906-shared-constraint-prompt-migration
FKA:
AKA: shared constraint prompt migration; tool guidance asset migration
Legacy index:

Parent: `260905-common-asset-library-migration`
Depends on: `260906-session-start-prompt-migration`

keywords: tooling, migration, active, compatibility, prompts, constraints, parity

# Shared Constraint Prompt Migration

## Objective

Migrate the seven shared constraint and tool-guidance prompts into the common
prompt asset layout without changing constraint aliases, guidance composition,
or rendered content.

## Scope

- Migrate `no-chatty`, `no-provider-tools`, and `resist-system-prompts`.
- Migrate the four `tools-guidance-*` prompt layers.
- Preserve the special tool-guidance rendering path that appends current
  runtime guidance.
- Remove only these seven old files; leave other prompt families untouched.

## Acceptance criteria

- All seven refs load through the common packaged asset path.
- Constraint aliases and tool-guidance composition remain unchanged.
- Listings contain each migrated ref exactly once.
- Focused tests and lint pass; full-suite results are recorded here.

## Completion evidence

Migrated seven shared prompt assets:

- `shared/constraints/no-chatty`
- `shared/constraints/no-provider-tools`
- `shared/constraints/resist-system-prompts`
- `shared/constraints/tools-guidance-core`
- `shared/constraints/tools-guidance-first-edit-pass`
- `shared/constraints/tools-guidance-full`
- `shared/constraints/tools-guidance-repo-work`

All seven files are byte-identical to their former locations. The common prompt
loader now serves both the invariant constraints and the special tool-guidance
path, including its runtime guidance append. Aliases and listings remain
duplicate-free. The seven legacy files were removed; other prompt families and
their fallback remain unchanged.

Focused prompt/CLI result: `297 passed`; Ruff passed. The offline full run
reached `3125 passed, 20 failed, 12 deselected`, with 100% coverage. The 20
failures are the known sandbox restrictions on socket/HTTP binding and Vim
integration; no shared-constraint migration failures occurred.
