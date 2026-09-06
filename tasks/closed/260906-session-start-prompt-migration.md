Filed as: 260906-session-start-prompt-migration
FKA:
AKA: role framing prompt migration; start here prompt migration
Legacy index:

Parent: `260905-common-asset-library-migration`
Depends on: `260906-dynamic-capability-asset-migration`

keywords: tooling, migration, active, compatibility, prompts, composition, parity

# Session-Start Prompt Migration

## Objective

Migrate the six frontmatter-backed session-start role and start-here prompts
into the common prompt asset layout without changing composition, metadata, or
public references.

## Scope

- Migrate the three `role-framing` prompts and three `start-here` prompts under
  `src/toas/assets/prompts/session-start/`.
- Route these refs through the common prompt loader.
- Preserve legacy category aliases and composition candidate resolution.
- Remove only these six old files; leave other prompt families untouched.

## Acceptance criteria

- All six prompts load with unchanged metadata and content.
- Direct, legacy category, and listing references remain available.
- Each migrated ref appears exactly once in listings.
- Focused tests and lint pass; full-suite results are recorded here.

## Completion evidence

Migrated six frontmatter-backed prompts:

- `session-start/role-framing/editorial-partner_v1`
- `session-start/role-framing/pragmatic-engineer_v1`
- `session-start/role-framing/requirements-interrogator_v1`
- `session-start/start-here/blank-page_v1`
- `session-start/start-here/collaborative-builder_v1`
- `session-start/start-here/spec-first_v1`

The migrated files are byte-identical to their former locations. The prompt
loader routes all six through the common packaged asset path while preserving
legacy category aliases, composition candidates, frontmatter metadata, and
duplicate-free prefix listings. The six old files were removed; other prompt
families and their fallback remain unchanged.

Focused prompt/runtime result: `349 passed`; Ruff passed. The offline full run
reached `3124 passed, 20 failed, 12 deselected`, with 100% coverage. The 20
failures are the known sandbox restrictions on socket/HTTP binding and Vim
integration; no session-start migration failures occurred.
