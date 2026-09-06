Filed as: 260906-config-discovery-acceptance-scenario
FKA:
AKA: operator config discovery journey; help-to-show acceptance; config topic acceptance
Legacy index:

Parent: `260905-common-asset-library-migration`
Depends on: `260906-config-show-acceptance-hardening`
Related: `260906-config-precedence-help-topic`; `260906-config-show-topic-sources`

keywords: surface, config, acceptance, usability, projection, follow-on

Claimed for implementation on 2026-09-06.

## Completion evidence

Added the pytest-BDD feature `config_discovery.feature` and operator-API-backed
steps in `test_config_discovery_steps.py`. The scenario runs:

```text
/help config models
/config show models
/config show models --sources
/config show --sources models
/help config sources
/help config provenance
```

It verifies compact filtered output, effective scalar defaults, legitimately
empty catalogs, equivalent source argument ordering, winning-source help, and
read-only behavior. A probe spy proves the journey performs no endpoint model
discovery and no live generation.

Acceptance result: `10 passed` with `-m acceptance`. Ruff passed. The full
suite reached `3115 passed, 20 failed, 10 deselected`, with 100% coverage; the
20 failures are the known sandbox restrictions on socket/HTTP binding and Vim
integration, unrelated to this scenario.

# Config Discovery Acceptance Scenario

## Objective

Encode the operator's config-discovery journey as an automated acceptance
scenario rather than relying on ad hoc manual verification.

## Scenario

```text
/help config models
/config show models
/config show models --sources
/config show --sources models
/help config sources
```

The scenario verifies conceptual discovery, curated topic inspection, winning
source projection, equivalent modifier ordering, precedence-help aliases, and
read-only behavior in one scratch workspace.

## Scope

- Add a pytest-BDD feature and operator-API-backed step implementation.
- Assert structural output rather than environment-specific values.
- Assert filtered views are compact and exclude the full inspection appendix.
- Assert model/base-url defaults are nonblank while unset catalogs may remain
  empty.
- Assert source projections are equivalent and no config updates or endpoint
  requests occur.

## Non-goals

- Do not test endpoint model discovery; that remains explicit follow-on work.
- Do not require live model generation or external network access.
- Do not duplicate every unit-level config/help assertion.

## Acceptance criteria

- The scenario runs in replay-only/local mode without network access.
- The complete help → show → sources journey passes through the operator API.
- Both `--sources` argument orders produce equivalent output.
- The scenario proves the filtered projection is compact and read-only.
- The scenario documents its structural invariants in the feature file.

## Allowed write surfaces

- `tests/acceptance/features/` and `tests/acceptance/steps/`;
- focused acceptance documentation if needed;
- this task file and generated `tasks/WORKBOARD.md` sections.

## Required completion evidence

- feature and step names;
- focused acceptance test result;
- full required test result;
- explicit note that no endpoint probe or live generation is involved.
