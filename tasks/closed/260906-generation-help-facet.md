Filed as: 260906-generation-help-facet
FKA:
AKA: generation plain help; paired generation facet; generation discovery
Legacy index:

Parent: `260905-common-asset-library-migration`
Depends on: `260906-config-discovery-acceptance-scenario`
Related: `260906-config-show-topic-sources`; `260901-help-system-design-survey`

keywords: surface, config, help, acceptance, generation, follow-on

Claimed for implementation on 2026-09-06.

## Completion evidence

Added the plain `generation` facet to the packaged help asset. The existing
generic route now renders:

```text
/help generation
help: generation
Generation turns a request into model output through thinking posture, output budgets, retry behavior, and transport shape.

configuration: /help config generation
```

The operator acceptance feature now includes the paired generation path through
`/help generation`, `/help config generation`, and `/config show generation`.
Focused catalog/step result: `287 passed`; acceptance result: `11 passed`;
Ruff passed. Full result: `3136 passed, 11 deselected`, with 100% coverage.

Extraction and execution facets remain intentionally deferred.

# Generation Help Facet

## Objective

Add the next small paired help facet so generation behavior can be explained
separately from the configuration controls that mutate it.

## Contract

```text
/help generation
  behavioral/invariant explanation
  → /help config generation

/help config generation
  configurable keys and exact next actions

/config show generation
  effective live generation values, compactly
```

The facet should describe thinking posture, output budgets, retries, and
transport shape without duplicating the config facet's key inventory.

## Scope

- Add the curated plain facet to the existing `generation` help topic asset.
- Reuse the existing generic plain-topic route and config topic identity.
- Extend the config discovery acceptance feature with a generation scenario.
- Preserve the intentionally small catalog and current config behavior.

## Non-goals

- Do not add extraction or execution facets in this slice.
- Do not change generation runtime semantics or defaults.
- Do not introduce a universal help registry.
- Do not add `/config help`.

## Acceptance criteria

- `/help generation` renders a concise behavioral explanation.
- The output points to `/help config generation`.
- `/help config generation` retains its related keys and next actions.
- `/config show generation` shows the related live keys without the full
  inspection appendix.
- The acceptance journey passes without network access or mutation.

## Allowed write surfaces

- `src/toas/assets/help/config.yaml`;
- the config discovery acceptance feature and steps;
- focused help/catalog tests;
- this task file and generated `tasks/WORKBOARD.md` sections.

## Required completion evidence

- rendered plain/config/live generation examples;
- acceptance and full test results;
- explicit note that extraction and execution remain deferred.
