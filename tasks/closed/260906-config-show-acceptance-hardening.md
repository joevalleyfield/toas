Filed as: 260906-config-show-acceptance-hardening
FKA:
AKA: config show compact projection; effective config display; operator config acceptance
Legacy index:

Parent: `260905-common-asset-library-migration`
Depends on: `260906-config-show-topic-sources`
Related: `260906-config-precedence-help-topic`; `260906-endpoint-model-discovery`

keywords: runtime, config, projection, acceptance, correctness, follow-on

Claimed for implementation on 2026-09-06.

## Completion evidence

Filtered `/config show` projections now stop after the selected values and a
small navigation footer; the full precedence/timing/quick-edit appendix
remains on bare `/config show`.

Representative default projection:

```text
llm.model = qwen3.5-35b-a3b    [source=default]
llm.models = ()                 [source=default]
llm.backends = ()               [source=default]
llm.base_url = http://localhost:8080/v1 [source=default]
backend.mode = external         [source=default]

next:
  /config show models --sources
  /help config models
```

The LLM scalar values now use the existing local `Settings.from_env()` default
path when the operator config contains its intentional blank sentinel. Catalog
collections remain empty when unset. No endpoint probe was added. Focused
result: `382 passed` (with `--no-cov`); Ruff passed. Full result: `3135 passed,
9 deselected`, with 100% coverage.

# Config Show Acceptance Hardening

## Objective

Make the operator acceptance path honest and compact for filtered config
inspection: topic-filtered views should show only their selected values, and
effective LLM defaults should not appear as blank unresolved sentinels.

## Observed failures

- `/config show models` appends the full unfiltered precedence, timing, policy,
  and quick-edit appendix.
- `OperatorConfig.llm.model` and `OperatorConfig.llm.base_url` may be blank by
  design while `Settings.from_env()` supplies their effective defaults; the
  current view prints blanks with `source=default`.

## Contract

```text
/config show
  full state and inspection guidance

/config show models
  selected model/backend values only, with compact navigation hints

/config show models --sources
  the same selected values plus winning sources
```

The filtered projection remains local, read-only, and network-free. Empty
catalog collections remain empty when no catalog is configured. Requested
configuration values remain distinct from any future endpoint-discovered
runtime observations.

## Scope

- Suppress the full inspection appendix for filtered `/config show` views.
- Add a compact filtered heading/navigation footer without duplicating help
  prose.
- Project effective default values for blank `llm.model` and `llm.base_url`
  using the existing local runtime settings default path.
- Preserve winning-source annotations and existing raw/topic filter behavior.
- Add operator acceptance tests for compactness, effective defaults, source
  projection, read-only behavior, and network-free execution.

## Non-goals

- Do not change configuration precedence or source calculation.
- Do not infer defaults for `llm.models` or `llm.backends`.
- Do not probe `/models` or any endpoint from `/config show`.
- Do not conflate requested model configuration with served model identity.
- Do not redesign the full unfiltered `/config show` appendix in this slice.

## Acceptance criteria

- Filtered output contains no full precedence/timing/quick-edit appendix.
- Blank configured LLM fields display their effective local defaults.
- Catalog collections remain empty when unset.
- `--sources` annotates displayed values with the winning source.
- Bare `/config show` retains its existing full inspection guidance.
- The operator acceptance scenario passes without mutation or network I/O.

## Allowed write surfaces

- the narrow `/config show` projection seam;
- focused operator/config acceptance tests;
- this task file and generated `tasks/WORKBOARD.md` sections.

## Required completion evidence

- compact filtered output example;
- default-value and source-label example;
- proof that bare `/config show` remains the detailed surface;
- focused and full required test results;
- explicit proof that endpoint discovery remains deferred to its separate task.
