Filed as: 260912-retire-global-model-catalog
FKA:
AKA: remove llm.models; retire global model catalog; endpoint-owned model knowledge
Legacy index:

Related: `260912-config-model-structured-view`; `260912-model-observation-raw-details`; `260906-endpoints-models-and-targets`

keywords: config, models, migration, inception, compatibility, contract

# Replace the global model catalog with named targets

## Pressure

The newer model surface has endpoint-associated catalogs, live observations,
and named targets. `llm.models` was intended to provide selectable model
choices, but its entries lack the endpoint, credentials, and generation context
that make a selection complete. Named targets provide that complete shape and
are intentionally global IDs, not endpoint-namespaced IDs.

## Current uses to replace or remove

- legacy `/model` model listing and fragmentary requested-model validation when
  no named target is configured; this is compatibility behavior, not a
  requirement of `/model`, `/model targets`, or `/model select TARGET`;
- global catalog rendering in `/config show models`;
- TOML load/save and config-key discovery;
- static configuration examples and tests.

## Resolved direction

`llm.models` should not survive as a parallel selectable-model concept. Its
selection role moves to named targets; its catalog role is already covered by
endpoint-associated known/observed models. Do not derive a replacement global
catalog.

The sole compatibility behavior is the explicit scalar `llm.model` selection
when no target-oriented configuration is available. That scalar remains a
valid config/file/environment input and must not be confused with endpoint-
reported availability or a named target.

The intended target shape permits short global names such as `luna`, `qwen`,
and `gemini`, each pointing to a different endpoint/model pair. Explicit
authoring already supports this; automatic promotion from known endpoint
models does not yet offer operator-chosen short IDs.

## Proposed migration order

1. Inventory and test all remaining behavioral consumers of `llm.models`.
2. Make endpoint catalogs/targets sufficient for model discovery and selection
   without changing the user-facing target contract; preserve globally scoped
   target IDs independent of endpoint identity.
3. Remove the no-target `/model` catalog listing and fragment validation path;
   retain only explicit scalar `llm.model` fallback resolution.
4. Remove `llm.models` from the valid-key, parser, serializer, help, and
   config structures. Existing files containing it should not silently create
   global model knowledge.
5. Cross-check save/load, `/models known|refresh`, `/model`, `/model targets`,
   `/model select TARGET`, and `/config show models` after removal.

## Follow-ons

Short-name promotion from endpoint catalogs, collision behavior when multiple
endpoints advertise the same model name, and richer catalog management remain
separate follow-ons. Explicit target authoring already provides the immediate
path for names such as `luna`, `qwen`, and `gemini`.

## Non-goals

- no change to live endpoint observation semantics;
- no conflation of requested model with served model;
- no new universal provider/model taxonomy;
- no removal of endpoint-associated catalogs or named targets.

## Status

Closed: 2026-09-12.

## Completion evidence

- Removed `ModelCatalogEntry` and `llm.models` from the config model,
  normalization, valid-key/parser, help, and flat serialization surfaces.
- Existing TOML `[llm] models` input is ignored during normalization rather
  than becoming global model knowledge; scalar `llm.model` remains available
  as the explicit fallback.
- Made `/model` target-oriented: bare `/model` reports the active target or
  scalar fallback, while selection is `/model select TARGET`; removed the
  legacy fragmentary `/model NAME` listing/validation path.
- Kept endpoint-owned known catalogs and named targets visible in structured
  `/config show models`; the exhaustive view remains available through
  `--flat` and `--sources`.
- Verification: `./scripts/check.sh` passed — 3231 tests, 17 deselected,
  acceptance checks, Ruff, and mypy; total coverage 100%.
