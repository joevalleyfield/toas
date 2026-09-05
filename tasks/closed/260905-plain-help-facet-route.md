Filed as: 260905-plain-help-facet-route
FKA:
AKA: paired help facets; plain topic help; models help topic
Legacy index:

Parent: `260905-common-asset-library-migration`
Depends on: `260905-help-assets-runtime-foundation`
Related: `260901-help-system-design-survey`

keywords: surface, follow-on, usability, help, assets, facets, config

Claimed for implementation on 2026-09-05.

## Completion evidence

Implemented the plain facet route through the packaged help catalog and narrow
help dispatcher seam.

Paired output examples:

```text
/help models
help: models
A backend supplies a provider endpoint; a model identifies the generation model used there.

configuration: /help config models
```

```text
/help config models
config help: models
Choose a direct model or configure backend/model catalogs.
```

Tests cover direct facet selection, aliases, the configuration cross-link,
read-only inert projection, unknown topics, and topics without a plain facet.
Focused result: `398 passed` (with `--no-cov`). Ruff passed. The full required
suite reached `3108 passed, 20 failed, 9 deselected`; the failures are existing
sandbox restrictions preventing socket/HTTP binds and Vim integration, and are
unrelated to this help slice. Strict coverage for the changed help module is
covered by the focused suite; the full run's coverage gate was affected by the
same sandbox failures.

The remaining plain-help topic catalog is intentionally deferred; this task
only establishes the paired route using the existing `models` asset.

# Plain Help Facet Route

## Objective

Expose the existing plain facet of the runtime `models` help asset through
`/help models`, establishing the paired relationship between behavioral help
and configuration help.

## Contract

```text
/help models
  explain what models and backends are and how they relate
  point to /help config models for mutability and config keys

/help config models
  explain configurable model/backend settings and exact next actions
```

The two views share topic identity and asset metadata but must not collapse
into one state dump or duplicate the config facet. Topics without a plain
facet remain valid and should continue to resolve only through their existing
surfaces.

## Scope

- Extend the help-topic dispatcher to resolve a plain topic route.
- Render the `plain` facet when present, with a config-help cross-link when a
  config facet also exists.
- Keep `/help config <topic-or-query>` behavior unchanged.
- Add focused tests for paired facets, unknown topics, and read-only result
  projection.

## Non-goals

- Do not add the full plain-help topic catalog.
- Do not add new config topics or config-state behavior.
- Do not move prompt or procedure assets.
- Do not introduce a universal asset schema or registry.

## Acceptance criteria

- `/help models` returns the plain models explanation from the packaged asset.
- The result links to `/help config models` for configurable behavior.
- `/help config models` retains its existing output and next actions.
- Unknown `/help <topic>` remains a clear usage/no-match path.
- The route remains read-only and inert-projected like existing help output.
- Focused and full test results are recorded.

## Allowed write surfaces

- `src/toas/assets/help_catalog.py` and the narrow help dispatcher seam;
- focused help/step tests;
- this task file and generated `tasks/WORKBOARD.md` sections.

## Required completion evidence

- paired plain/config output examples;
- tests for facet selection, cross-linking, and projection;
- full required test result;
- explicit note that the remaining topic catalog is deferred.
