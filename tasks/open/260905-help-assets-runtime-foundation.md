Filed as: 260905-help-assets-runtime-foundation
FKA:
AKA: runtime help assets; config help asset slice; help asset loader
Legacy index:

Parent: `260905-common-asset-library-migration`
Depends on: `260901-help-system-design-survey`
Related: `260905-common-asset-library-migration`; `260904-config-help-state-feedback`

The first prerequisite for the help-backed onward path is
`260905-config-show-filters`, which defines the small read-only state-query
surface before help assets begin linking to filtered inspection.

keywords: surface, migration, follow-on, usability, config, search, assets, help

# Runtime Help Assets Foundation

## Objective

Implement the first vertical slice of runtime-loadable help assets so
configuration help can move out of hardcoded source prose without requiring a
greedy migration of prompts or procedures.

This is the first child of the common asset-library migration. It should prove
the help-asset contract and the minimum shared resource-loading mechanics that
help needs; it does not need to complete the entire `assets/` migration.

## Product contract

Help assets are static conceptual material with optional facets. A topic may
have a plain-help facet, a config-help facet, both, or neither. The config
facet supports compact explanations, aliases, related config keys, and onward
links to inspection/value/mutation commands. Live values and allowed choices
remain runtime/config data, not duplicated asset content.

The first configuration path should support:

```text
/help config
/help config <topic-or-query>
```

The query path combines curated topic lookup with implicit apropos-like search
over config key names and descriptions. A curated match leads with a compact
explanation, then related keys and next actions. Search-only matches identify
the matching key or description. The same vocabulary may later serve
`/config show` filters, but this task does not need to implement those filters.

## Scope

- Define the smallest shared asset primitives needed by help: safe resource
  references, loading, listing/lookup, metadata, and static provenance.
- Add a help asset family under the target `assets/` package shape, using a
  format that can represent topic identity, aliases, optional facets, summary,
  related keys, and onward actions.
- Add a runtime help loader and search path for configuration topics.
- Move the config-help overview and at least one representative curated topic
  into assets, with key/description search demonstrated by tests.
- Wire the existing help surface to the asset-backed path while preserving its
  result/projection and read-only behavior.
- Document the boundary between asset-owned conceptual guidance and
  config-owned live state/value/provenance reporting.

## Non-goals

- Do not migrate prompt or procedure directories in this slice.
- Do not create a universal schema or semantic registry for all asset families.
- Do not require the full curated topic set to be settled before proving the
  loader and one vertical slice.
- Do not implement `/config show` filters, config mutations, or live state
  rendering as part of help assets.
- Do not preserve a second hardcoded config-help implementation after the
  asset-backed path is authoritative; compatibility should be at public
  command behavior, not duplicated content.

## Acceptance criteria

- Help assets are packaged, safely addressable, and loadable at runtime.
- The asset format supports optional plain/config facets without requiring
  every topic to have both.
- `/help config` renders from help assets and remains compact/read-only.
- `/help config <query>` supports curated-topic lookup and implicit search over
  config key names and descriptions.
- At least one curated topic produces an up-front explanation, related keys,
  and exact onward actions such as `/config show` or `/config values <key>`.
- Search results distinguish exact key, alias, description, and topic matches
  sufficiently for an operator to understand why a result appeared.
- Missing, malformed, and traversal-invalid assets fail clearly and safely.
- Existing prompt/procedure behavior is unchanged, with no prompt/procedure
  relocation required by this task.
- Tests cover loader safety, metadata/facet parsing, curated lookup,
  search-only lookup, no-match behavior, and help result projection.

## Allowed write surfaces

- `src/toas/assets/` and its help-specific implementation/assets;
- the existing help runtime seam and narrow loader wiring;
- focused help/runtime tests;
- this task file and generated `tasks/WORKBOARD.md` sections;
- a concise design-note update if the asset contract changes materially.

## Required completion evidence

- example asset tree and format description;
- one end-to-end asset-backed `/help config` path;
- search behavior examples for curated and uncurated queries;
- tests and results for safety, parsing, and projection parity;
- explicit list of deferred prompt/procedure migration work.
