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

Elaborated; ready for implementation.

## Elaboration

### Grounding: what `/config show` actually has today

The renderer is `_config_show_result` in
`src/toas/runtime/operator_command_config_help.py`. Unfiltered behavior is:
`flat = flatten_config(context.config)` (with the `llm.base_url`/`llm.model`
env-fallback patch in `_effective_config_values`), then one
`key = value` line per key, plus a precedence-stack epilogue. `--sources`
adds `[source=...]` per line from `context.config_sources`.

Two properties of the flat dict drive the design:

- `flatten_config` uses `asdict`, so list/tuple fields (`llm.endpoints`,
  `llm.targets`, `llm.models`, `generation.avoid_terms`,
  `shell.allowed_commands`, `runtime.*_runtime`, `prompt.constraints`,
  `backend.managed_local.*`, `extraction.*`) are dumped as raw Python
  literals. This is the "dumping complete catalogs" failure the task forbids.
- The flat dict has **no notion of the active model**. `llm.base_url` /
  `llm.model` are legacy top-level LLM fields; the real selection is a
  target id carried in the event log. The current view therefore
  misrepresents which model is actually in play.

### What is already available in context (no new plumbing)

`OperatorCommandContext` already exposes everything the overview needs:

- `context.events` -> `active_target_selection(events)` (graph /
  `graph_control_state_edges.active_target_selection`) gives the active
  target id, or `None`.
- `context.config` -> `resolve_model_target` + `resolve_target_invocation`
  (`src/toas/runtime/model_targets.py`) resolve that target into a concrete
  `Settings` (base_url, model, transport) plus `endpoint_source`,
  `model_source`, and `api_key_source` *labels* — not secret values.
  `infer_endpoint_default_model` already returns a source tag
  (`endpoint:...:default_model`, `config:llm.model:single_endpoint`,
  `env_or_default`, `unresolved`) for free.
- `context.config_sources` (built by `build_config_sources`) already labels
  every valid key as `session_override` / `config_file` / `env` /
  `default`. That is the raw material for `(default)` vs `(unset)`
  distinction.

So the "models" section can show **real active state** (active target id,
resolved endpoint base_url, resolved model, transport, and concise
endpoint/target/model counts) rather than re-serializing legacy keys.

### Proposed semantic sections (effective values, not storage shape)

A small rendering helper builds an ordered list of sections. Each row is a
semantic label -> effective value with an explicit state marker. Sections
and their keys:

- **models** (highest signal; leads the view)
  - active target: id or `(none)`.
  - active endpoint: resolved base_url, or `(unset)` when no target / no
    endpoint. Show the `endpoint_source` tag inline when it is not the
    trivial `target:default`.
  - active model: resolved model, or `(unresolved)` when the chain did not
    converge; carry the `model_source` tag.
  - transport: effective transport mode for the active invocation.
  - counts: `N endpoints · M targets · K models` (counts only; never the
    catalog bodies).
- **generation**
  - thinking_mode, thinking_budget_tokens (show `0` as `(unset)` budget),
    max_tokens (`0` = `(auto/unset)`), max_retries, retry_delay_s,
    transport_mode, and a short `avoid_terms` summary (count or first few,
    not the full tuple).
  - When a target is active, these reflect the *target-overlaid* policy
    (`resolve_target_generation`); otherwise the global `config.generation`.
- **extraction**
  - intent_arbitration, shell_staging, projection_shape, and the boolean
    gates (user_shell, operator_command, loose_command_fallback). Keep
    `yaml_position` as a compatibility note, not a headline row.
- **execution**
  - backend.mode (and a one-word managed_local hint only when
    `mode == "managed_local"`), shell.assistant_timeout_s,
    tool_writes.newline_style.
- **navigation** (footer, not data)
  - Hints for topic views (`/config show models|generation|extraction|
    execution`) and provenance (`/config show <topic> --sources`), plus the
    structured lane commands (`/config endpoint list`, `/config target
    list`) where structured detail lives.

Sections with nothing to show collapse to a single `(defaults only)` line
rather than a wall of identical default rows.

### State markers: distinguishing empty / unset / default

Use `context.config_sources` as the discriminator, resolved per key:

- value present and source is `session_override` or `config_file` or
  `env` -> render the effective value plainly (this is "set").
- value equals the dataclass default and source is `default` -> render
  `<value> (default)`.
- a field that is legitimately absent/empty (e.g. no active target,
  unresolved model) -> render `(none)` / `(unresolved)`.

This keeps "set to the default value" visually distinct from "left at the
built-in default" without inventing new storage.

### Secret boundary (what must never render)

The only secret-bearing material in this domain is the API key. It is
never a flat config key: `EndpointCatalogEntry`/`LLMPolicy` carry
`api_key_source` + `api_key_ref` (labels), and `resolve_secret` produces the
actual value only at invocation time. `RUNTIME_SECRETS["llm_api_key"]`
holds in-memory secret values. The overview therefore must:

- render `api_key_source`/`api_key_ref` as source labels only (e.g.
  `env:TOAS_LLM_API_KEY`), never a resolved key;
- never call `resolve_secret` in the rendering path;
- show API-key presence as a marker at most (e.g. `api_key: (set via
  env:TOAS_LLM_API_KEY)` or `(runtime secret)` when
  `RUNTIME_SECRETS` has the key), never the value.

Add a regression test that seeds a runtime secret and an endpoint
`api_key_ref`, runs unfiltered and filtered `/config show`, and asserts the
secret value and any raw key string are absent from the rendered output.

### Filtered and `--sources` compatibility

- `/config show TOPIC` keeps `_config_key_matches` as the key selector and
  the `no matching keys` / `next:` footer contract. The only intentional
  change is that a *topic* that maps to one of the four semantic sections
  renders grouped rows for that section instead of a flat slice; free-text
  and dotted-key filters still render the matched `key = value` rows.
  `resolve_config_help_keys` already maps topic words to key sets and is the
  natural place to also map to section names.
- `--sources` keeps winning-source semantics from
  `context.config_sources`; in the overview it annotates the shown rows
  rather than emitting every key.

### Legacy top-level LLM fields

`llm.base_url` / `llm.model` (and their env fallback in
`_effective_config_values`) are presented in the models section as
*fallbacks/defaults* — the "no active target" path — not as the primary
structure. The primary structure is the active target resolution above.

### Where the code lives

- New grouping/formatting helpers + section definitions: a focused module
  or section within `src/toas/runtime/operator_command_config_help.py`
  (the command already owns rendering and `_result_node`). Keep them pure
  functions of `(OperatorConfig, sources, active_target_id, events)` so
  they are trivially unit-testable without a live step.
- Reuse, do not reimplement: `active_target_selection`,
  `resolve_model_target`, `resolve_target_invocation`,
  `resolve_target_generation`, `build_config_sources`/source labels.
- Tests: focused unit tests for the section builder (configured vs
  mostly-default fixtures), secret-absence assertions, and filtered /
  `--sources` regression tests.

### Open questions to resolve during implementation (do not block elaboration)

- Does `resolve_target_invocation` need `base_settings` from
  `settings_for_runtime`? It does — confirm the command path already
  resolves base settings, or resolve them inside the renderer via the
  same `settings_for_runtime(context.config, ...)` the rest of the command
  uses, passing `RUNTIME_SECRETS` for source labels (labels only, never
  the key).
- Exact set of keys that count as "extraction booleans" worth a row vs. a
  collapsed summary — decide against the "avoid dumping every key" goal.
- Whether `execution` should surface `runtime.streaming_mode` /
  `context_budget_mode`; default is to leave them to filtered views.

### Suggested implementation cadence

1. Red: unit test the section builder on a fully-configured fixture and a
   mostly-default fixture, including secret-seeding and the active-target
   path (will fail: no builder exists).
2. Green: implement the pure builder + wire it into
   `_config_show_result` for the unfiltered case only.
3. Refactor: map topic filters onto sections, keep `--sources` annotation,
   run targeted coverage then the full suite.
intent: Write the grounded elaboration into the task, preserving all prior sections and the status
