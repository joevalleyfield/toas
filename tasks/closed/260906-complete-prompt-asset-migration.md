Filed as: 260906-complete-prompt-asset-migration
FKA:
AKA: full prompt asset sweep; prompt legacy removal
Legacy index:

Parent: `260905-common-asset-library-migration`
Depends on: `260906-shared-constraint-prompt-migration`

keywords: tooling, migration, active, compatibility, prompts, parity, removal

# Complete Prompt Asset Migration

## Objective

Complete the file-backed prompt migration: move the remaining prompt corpus into
`src/toas/assets/prompts/`, cut the prompt loader over to the common asset
boundary, and remove the legacy prompt tree.

## Scope

- Migrate every remaining `.txt` prompt, including the two temporary duplicate
  compatibility copies.
- Preserve prompt frontmatter, composition, dynamic rendering, aliases, and
  public references.
- Make static prompt loading and listing asset-only.
- Remove the old `src/toas/prompts/` files and legacy prompt package-data entry.
- Keep dynamic prompt renderers registered in code while their templates remain
  file-backed under assets.

## Acceptance criteria

- All original 48 prompt definitions exist under `assets/prompts/` exactly once.
- No runtime prompt code reads the old prompt directory.
- Prompt composition, constraints, dynamic capability rendering, listing, and
  missing-asset behavior remain covered.
- Focused tests and lint pass; full-suite results are recorded here.

## Completion evidence

The complete original prompt corpus is now under `src/toas/assets/prompts/`:

- 48 `.txt` prompt assets exist in the final asset tree.
- 0 legacy `.txt` prompt files remain under `src/toas/prompts/`.
- `list_prompt_assets()` returns 48 unique refs.
- The old prompt package-data entry and runtime directory reads are removed.

Static prompt loading and listing now use the common packaged asset loader.
Dynamic capability renderers remain code-registered but load their templates
from the same asset tree. Prompt frontmatter, composition candidates, legacy
category aliases, constraint rendering, runtime guidance append, and missing
prompt/prefix behavior remain covered. The historical
`pragmatic-default_v2.golden.md` fixture remains under the old directory for
its existing test comparison; it is not a runtime prompt asset.

Focused prompt/runtime result: `616 passed`; Ruff passed. The offline full run
reached `3125 passed, 20 failed, 12 deselected`, with 100% coverage. The 20
failures are the known sandbox restrictions on socket/HTTP binding and Vim
integration; no prompt migration failures occurred.
