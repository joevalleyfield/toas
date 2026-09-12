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

- legacy `/model` model listing and requested-model validation when no endpoint
  is selected;
- global catalog rendering in `/config show models`;
- TOML load/save and config-key discovery;
- static configuration examples and tests.

## Design questions

1. Should global model knowledge disappear completely, or should a read-only
   aggregate be derived from endpoint catalogs and observations?
2. If `/model` remains a compatibility surface, should it list named targets,
   endpoint-qualified models, or only the active endpoint's catalog?
3. Does any workflow need curated model metadata independent of an endpoint?
   If so, should that become target metadata rather than a global catalog?
4. What should happen to files containing `llm.models`: explicit migration,
   warning, or silent discard after a bounded compatibility period?

## Proposed migration order

1. Inventory and test all remaining behavioral consumers of `llm.models`.
2. Make endpoint catalogs/targets sufficient for model discovery and selection
   without changing the user-facing target contract.
3. Migrate or retire the legacy `/model` fallback behavior explicitly.
4. Remove `llm.models` from the valid-key, parser, serializer, help, and
   config structures; retain only a time-bounded read-time transition if
   required for existing files.
5. Cross-check save/load, `/models known|refresh`, `/model targets`, and
   `/config show models` after removal.

## Non-goals

- no change to live endpoint observation semantics;
- no conflation of requested model with served model;
- no new universal provider/model taxonomy;
- no removal of endpoint-associated catalogs or named targets.

## Status

Inception: confirm the replacement for legacy global model listing and the
compatibility window before implementation.
