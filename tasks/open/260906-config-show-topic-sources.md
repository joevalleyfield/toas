Filed as: 260906-config-show-topic-sources
FKA:
AKA: topic-aware config show; config show provenance; related key inspection
Legacy index:

Parent: `260905-common-asset-library-migration`
Depends on: `260905-help-assets-runtime-foundation`; `260905-config-show-filters`
Related: `260905-plain-help-facet-route`; `260906-config-precedence-help-topic`

keywords: runtime, config, projection, provenance, usability, follow-on

# Topic-Aware Config Show With Sources

## Objective

Complete the progressive-disclosure path from config help to live state by
making curated config topics valid filters for `/config show`, including the
orthogonal `--sources` modifier.

## Contract

```text
/help config models
  → /config show models
  → /config show models --sources
```

When `models` resolves as a curated topic, inspection selects the topic's
declared related keys (`llm.model`, `llm.models`, `llm.backends`,
`llm.base_url`, and `backend.mode`, subject to the current valid-key set).
With `--sources`, each selected effective value includes its winning source.

Raw exact-key, prefix, token, and no-match filters remain supported. Topic
resolution changes selection vocabulary only; `--sources` changes projection
only and may appear before or after the filter.

## Scope

- Reuse the packaged help catalog's topic identity and related-key metadata.
- Extend `/config show` selection to resolve curated config topics before raw
  key filtering.
- Preserve current ordering and omit topic-declared keys absent from the live
  flattened config.
- Preserve `--sources` as a composable winning-source enrichment.
- Add focused tests for topic selection, source enrichment, argument order,
  raw-filter compatibility, missing keys, and read-only projection.

## Non-goals

- Do not change source precedence calculation or source labels.
- Do not show the entire precedence chain per key.
- Do not make `/config show` mutate or persist anything.
- Do not introduce a universal registry beyond the existing help catalog.

## Acceptance criteria

- `/config show models` displays all currently valid related model/backend keys.
- `/config show models --sources` displays those values with winning sources.
- `/config show --sources models` is equivalent.
- Existing exact, prefix, token, and no-match filters retain their behavior.
- Help links form a working conceptual-to-live-state path.
- Tests verify inert read-only output and no config updates.

## Allowed write surfaces

- the narrow `/config show` dispatcher/selection seam;
- `src/toas/assets/help_catalog.py` only if a small shared resolver is needed;
- focused config/help tests;
- this task file and generated `tasks/WORKBOARD.md` sections.

## Required completion evidence

- paired output examples with and without `--sources`;
- focused and full required test results;
- explicit note that winning source is the only provenance detail exposed.
