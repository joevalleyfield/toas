Filed as: 260912-retire-global-model-catalog
FKA:
AKA: remove llm.models; retire global model catalog; endpoint-owned model knowledge
Legacy index:

Related: `260912-config-model-structured-view`; `260912-model-observation-raw-details`; `260906-endpoints-models-and-targets`

keywords: config, models, migration, inception, compatibility, contract

# Retire the global `llm.models` catalog

## Pressure

The newer model surface has endpoint-associated catalogs, live observations,
and named targets. The global `llm.models` collection duplicates model
knowledge without identifying which endpoint serves it, while still feeding
the legacy `/model` availability/listing path and the config display.

## Current uses to replace or remove

- legacy `/model` model listing and fragmentary requested-model validation when
  no named target is configured; this is compatibility behavior, not a
  requirement of `/model`, `/model targets`, or `/model select TARGET`;
- global catalog rendering in `/config show models`;
- TOML load/save and config-key discovery;
- static configuration examples and tests.

## Resolved direction

`llm.models` has no coherent legacy behavior worth retaining. It is not a
fallback catalog, a meaningful validation space, or a substitute for named
targets. Remove it rather than deriving a replacement aggregate.

The sole compatibility behavior is the explicit scalar `llm.model` selection
when no target-oriented configuration is available. That scalar remains a
valid config/file/environment input and must not be confused with endpoint-
reported availability or a named target.

## Proposed migration order

1. Inventory and test all remaining behavioral consumers of `llm.models`.
2. Make endpoint catalogs/targets sufficient for model discovery and selection
   without changing the user-facing target contract.
3. Remove the no-target `/model` catalog listing and fragment validation path;
   retain only explicit scalar `llm.model` fallback resolution.
4. Remove `llm.models` from the valid-key, parser, serializer, help, and
   config structures. Existing files containing it should not silently create
   global model knowledge.
5. Cross-check save/load, `/models known|refresh`, `/model`, `/model targets`,
   `/model select TARGET`, and `/config show models` after removal.

## Non-goals

- no change to live endpoint observation semantics;
- no conflation of requested model with served model;
- no new universal provider/model taxonomy;
- no removal of endpoint-associated catalogs or named targets.

## Status

Ready for implementation.
