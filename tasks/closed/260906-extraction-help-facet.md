Filed as: 260906-extraction-help-facet
FKA:
AKA: extraction plain help; extraction discovery; intent extraction facet
Legacy index:

Parent: `260905-common-asset-library-migration`
Depends on: `260906-generation-help-facet`
Related: `260901-help-system-design-survey`; `260803-tool-intent-ingress-separation`

keywords: surface, config, help, acceptance, extraction, follow-on

Claimed for implementation on 2026-09-06.

## Completion evidence

Added the curated `extraction` topic with `intent`, `intents`, and
`arbitration` aliases. The plain facet establishes the invariant boundary:

```text
/help extraction
help: extraction
Extraction preserves authored source order and lane boundaries while selecting intent candidates; it does not execute them.

configuration: /help config extraction
```

The config facet exposes the extraction controls and `/config show extraction`
now provides their compact live projection. The acceptance feature covers the
paired path and explicitly asserts the non-executing boundary.

Focused result: `289 passed`; acceptance result: `12 passed`; Ruff passed.
Full result: `3138 passed, 12 deselected`, with 100% coverage.

Execution remains intentionally deferred; extraction help does not imply
execution or authorization.

# Extraction Help Facet

## Objective

Add a paired extraction help topic where the existing corpus supports a clear
distinction between invariant intent discovery/arbitration behavior and its
configuration controls.

## Contract

```text
/help extraction
  candidate discovery, lane boundaries, and arbitration invariants
  → /help config extraction

/help config extraction
  configurable extraction keys and exact next actions

/config show extraction
  effective live extraction values, compactly
```

The plain facet should explain that extraction identifies candidate
operator/tool/shell intent from authored content and preserves source-order and
lane boundaries before any later execution or authorization decision.

## Scope

- Add the curated plain facet to a new `extraction` config-help topic asset.
- Reuse the generic plain-topic route and topic-aware config inspection.
- Extend the config discovery acceptance feature with an extraction scenario.
- Include the existing compatibility distinction for `yaml_position` without
  making it the primary extraction model.

## Non-goals

- Do not add an execution facet or imply extraction executes anything.
- Do not change extraction, arbitration, shell, or projection semantics.
- Do not introduce a universal help registry or `/config help`.
- Do not broaden the catalog beyond this concrete topic.

## Acceptance criteria

- `/help extraction` renders a concise invariant explanation.
- The output points to `/help config extraction`.
- `/help config extraction` exposes related keys and next actions.
- `/config show extraction` is compact and shows the related live values.
- The acceptance journey remains local, read-only, and network-free.

## Allowed write surfaces

- `src/toas/assets/help/config.yaml`;
- focused help/catalog tests;
- the config discovery acceptance feature and steps;
- this task file and generated `tasks/WORKBOARD.md` sections.

## Required completion evidence

- rendered plain/config/live extraction examples;
- acceptance and full test results;
- explicit note that execution remains deferred and extraction does not imply execution.
