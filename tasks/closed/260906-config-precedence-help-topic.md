Filed as: 260906-config-precedence-help-topic
FKA:
AKA: config sources help; provenance help; precedence topic
Legacy index:

Parent: `260905-common-asset-library-migration`
Depends on: `260905-help-assets-runtime-foundation`
Related: `260905-plain-help-facet-route`; `260901-help-system-design-survey`

keywords: surface, config, help, search, provenance, usability, follow-on

Claimed for implementation on 2026-09-06.

## Completion evidence

Added the curated `precedence` topic to the packaged configuration-help asset
with `sources` and `provenance` aliases. All forms render the same focused
guidance and link to `/config show <topic> --sources`.

Representative output:

```text
/help config sources
config help: precedence
The effective value comes from the highest-precedence source that provides it; source output identifies that winning source only.

next:
  /config show <topic> --sources
```

The compact `/help config` overview and existing key search remain unchanged.
Focused result: `400 passed` (with `--no-cov`); Ruff passed. Full result:
`3131 passed, 9 deselected`, with 100% coverage.

Source terminology intentionally exposes the winning source only; no
full-provenance view was added.

# Config Precedence Help Topic

## Objective

Make configuration precedence and winning-source semantics discoverable as a
focused, searchable config-help topic.

## Contract

```text
/help config precedence
/help config sources
/help config provenance
```

These aliases explain the precedence order, clarify that `/config show` reports
the effective value, and point to `/config show <topic> --sources` for the
winning source of each displayed value.

The compact `/help config` overview may retain its short precedence reminder;
the focused topic is the canonical detailed explanation and searchable home.

## Scope

- Add a curated `precedence` config topic to the packaged help asset.
- Add aliases for `sources` and `provenance`.
- State explicitly that source output identifies the winning source only, not
  the complete precedence chain.
- Link the topic to source-enriched config inspection.
- Add tests for topic resolution, aliases, output, and inert projection.

## Non-goals

- Do not change precedence calculation or source labels.
- Do not add a full provenance-history view.
- Do not duplicate the complete `/config show` output in help.
- Do not expand the general help catalog.

## Acceptance criteria

- All three topic forms resolve to the same focused help.
- The output explains precedence and winning-source semantics compactly.
- The output points to `/config show <topic> --sources`.
- Existing `/help config` overview and key search behavior remain intact.
- Tests verify read-only inert projection and unknown-topic behavior.

## Allowed write surfaces

- `src/toas/assets/help/config.yaml` and its narrow help rendering seam;
- focused help/catalog tests;
- this task file and generated `tasks/WORKBOARD.md` sections.

## Required completion evidence

- rendered examples for `precedence`, `sources`, and `provenance`;
- focused test result and full required test result;
- explicit confirmation that source means winning source only.
