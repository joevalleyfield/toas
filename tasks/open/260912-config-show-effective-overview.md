Filed as: 260912-config-show-effective-overview
FKA:
AKA: config overview; effective config dashboard; grouped config show
Legacy index:

Parent: `260912-model-observation-raw-details`
Related: `260907-source-reference-operation-shorthand`

keywords: config, surface, projection, implementation, usability, active

# Make unfiltered config show an effective-state overview

## Objective

Replace the current flat key/value dump produced by unfiltered `/config show`
with a compact, grouped overview of effective runtime state. Preserve filtered
inspection for detailed key/configuration views and `--sources` for provenance.

## User contract

```text
/config          compact usage and navigation
/config show     effective state at a glance
/config show X   inspect a topic or matching configuration keys
/config show --sources X
```

The unfiltered view should group high-signal state under semantic sections:

- models: active target, endpoint, requested model, and concise counts;
- generation: thinking, output budget, retries, and transport;
- extraction: arbitration and staging;
- execution: backend mode, shell timeout, and tool-write policy;
- navigation hints for topic-specific and provenance views.

It must show effective values, not storage-shaped dictionaries; use explicit
markers such as `(none)`, `(unset)`, or `(default)` rather than blank values;
never reveal secret values; and avoid dumping complete catalogs or every key.

## Acceptance criteria

- Unfiltered `/config show` is grouped and compact rather than a flat
  key=value serialization.
- The overview exposes active model/endpoint state and representative runtime
  settings without pretending to be exhaustive.
- Structured endpoint/catalog/target details remain available through the
  filtered models/endpoints/targets views.
- `--sources` remains the explicit provenance view and retains winning-source
  semantics.
- Legacy top-level LLM fields are represented as model defaults/fallbacks in
  the overview rather than promoted as the primary conceptual structure.
- Empty, unset, and default values are visibly distinct where relevant.
- Secret values and secret material remain absent from all rendered output.
- Existing filtered `/config show TOPIC` behavior remains compatible except for
  intentional vocabulary/grouping improvements.

## Non-goals

- No removal or migration of legacy configuration inputs in this slice.
- No new configuration keys or changes to precedence semantics.
- No redesign of structured endpoint/target authoring commands.
- No machine-readable output mode yet.

## Allowed write surfaces

- config overview rendering and its semantic grouping helpers;
- focused unit/acceptance tests;
- help assets or usage text needed to expose the views;
- this task and generated `tasks/WORKBOARD.md` sections.

## Required completion evidence

- Representative overview examples for configured and mostly-default states;
- assertions that secrets are not rendered;
- filtered and `--sources` regression coverage;
- focused and full verification results.

## Status

Ready for implementation.
