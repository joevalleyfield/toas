Filed as: 260912-model-observation-raw-details
FKA:
AKA: model observation raw responses and detail projection
Legacy index:

Parent: `260905-common-asset-library-migration`
Related: `260907-source-reference-operation-shorthand`

keywords: models, endpoints, observation, catalog, raw, details, discovery

# Expose raw model observations and seed detail projection

## Objective

Make live endpoint observations inspectable enough to discover and implement
model-detail extractors without conflating endpoint protocol, configured
selection, and observed model identity.

## User contract

```text
/models live ENDPOINT
/models live ENDPOINT --details
/models live ENDPOINT --raw
/models refresh ENDPOINT
/models refresh ENDPOINT --details
/models refresh ENDPOINT --raw
/models known ENDPOINT
/models known ENDPOINT --details
```

- The default live view reports endpoint identity, URL, protocol, status, and
  concise advertised model names.
- A path-like model identifier is displayed by basename while its raw value is
  retained for provenance and catalog identity.
- `--raw` is valid only for `live` and `refresh`; it exposes the actual HTTP
  response body/envelope or HTTP failure body, without pretending it is
  normalized catalog data.
- `--details` is valid for all three operations but initially provides an
  honest, stable stub for fields not yet extracted, pointing to `--raw` where
  appropriate.
- `refresh` reports the newly added model names in its default quiet result,
  along with the resulting known count. An empty delta is explicit.
- Requested model and active target are optional, separately labeled context;
  they are not presented as advertised or served model data.
- The endpoint access protocol is labeled as protocol (for example,
  `openai-compatible`), not provider, unless provider identity is explicitly
  known.

## Phased implementation plan

1. Extend the `/models` argument grammar and help with the operation-scoped
   `--raw` and `--details` flags, rejecting unsupported combinations clearly.
2. Preserve the raw HTTP response/failure body through live observation and
   refresh rendering without changing the known catalog contract.
3. Normalize display names for path-like identifiers while retaining raw
   identifiers and stable observation provenance.
4. Change refresh’s default result to include the added model names and known
   count, including the no-new-models case.
5. Add the `--details` stub and tests for its shape; leave concrete field
   extraction as follow-on work driven by captured raw endpoint responses.

## Acceptance criteria

- `live --raw` displays the exact successful response body and a failed HTTP
  response body without network-independent catalog substitution.
- `refresh --raw` displays the fresh response while preserving its catalog
  update semantics.
- `known --raw` is rejected with a useful usage explanation.
- Default refresh output names every newly added model and reports the final
  known count; repeated refreshes report an explicit empty delta.
- Default output uses `protocol`, never `provider: openai` merely because the
  endpoint is OpenAI-compatible.
- Path-like observed identifiers display by basename, with raw identity still
  available in raw/details output or durable provenance.
- `--details` is discoverable, stable, and explicitly incomplete rather than
  silently dropping endpoint-specific fields.
- Existing live/known/refresh behavior and network-free known inspection remain
  compatible apart from the intentional output improvements.

## Non-goals

- No universal provider-detection heuristic.
- No assumption that all endpoints expose the same model metadata schema.
- No requirement to persist complete raw HTTP envelopes in the catalog.
- No model selection or target-authoring changes.
- No implementation of every detail extractor in this slice.

## Allowed write surfaces

- `/models` operator command and model-observation runtime modules;
- focused unit/acceptance tests;
- help assets and command usage text;
- this task file and generated `tasks/WORKBOARD.md` sections.

## Required completion evidence

- Successful and failed raw-observation examples;
- live, refresh, and known flag-combination tests;
- refresh delta examples for added and empty cases;
- explicit note identifying which detail fields remain deferred;
- focused and full verification results.

## Status

Ready for implementation.
