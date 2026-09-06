# Endpoints, Models, Backends, and Targets

Status: DESIGN / SEMANTIC MAPPING
Date: 2026-09-06
Related task: `260906-endpoint-model-discovery`
Related notes: `2026-06-28-llm-backend-generalization-and-gemini-discovery`; `2026-09-01-help-system-design`

## Insight

TOAS currently uses “backend”, “endpoint”, “model”, and “catalog” across
several overlapping configuration and operator surfaces. The existing form is
useful enough to operate, but it combines distinct meanings:

- how inference is provided;
- where an inference API is reached;
- which model is requested;
- which models are known or observed;
- which complete configuration is currently selected.

The next design direction is to tease these meanings apart before adding
high-profile `/model`, `/models`, or target-selection behavior.

## Current mapping

| Current representation | Observed behavior | Actual semantic owner |
| --- | --- | --- |
| `llm.base_url` | Scalar URL for the default runtime | Implicit endpoint |
| `llm.provider` | Global transport/provider selection | Endpoint protocol, currently over-global |
| `llm.model` | Scalar requested model | Implicit target |
| `llm.models` | Global static model catalog | Known-model catalog |
| `llm.backends[].id` | Named selection key | Endpoint identity today |
| `llm.backends[].base_url` | Endpoint URL | Endpoint connection |
| `llm.backends[].api_key_*` | Endpoint credential lookup | Endpoint authentication |
| `llm.backends[].models` | Static model IDs associated with a named URL | Endpoint-associated known-model catalog |
| `llm.backends[].model` | Default requested model for a named URL | Default target/model association |
| `backend.mode` | `external` or `managed-local` execution mode | Backend execution mechanism |
| `backend.managed_local` | Process command, cwd, env, health URL | Backend lifecycle |
| `backend_startup.*` | Startup-only backend settings | Backend runtime |
| `generation.*` | Global generation behavior | Default target generation settings |
| `/backend NAME` | Selects a named `llm.backends[]` entry | Endpoint selection under the wrong name |
| `/model NAME` | Selects a requested model ID | Target fragment, not a complete target |

## Semantic model

The intended vocabulary is:

```text
backend
  The execution mechanism and lifecycle: external service, managed-local
  service, or a future in-process inference engine.

endpoint
  An API or inference surface exposed by or connected to a backend. It owns
  provider protocol, URL or equivalent connection details, credentials, and
  discovery behavior.

model
  A requested model identifier or an endpoint-reported model identifier.

model catalog
  Durable operator knowledge of model identifiers, global or associated with
  an endpoint.

model observation
  Ephemeral runtime data returned by an explicit live endpoint probe.

target
  A named durable selection recipe combining an endpoint/backend choice, a
  requested model, and embedded generation settings.

active selection
  A session-level reference to a named target.
```

The endpoint may be optional for a future in-process backend. No in-process
implementation is implied by reserving that space.

## Confirmed behavior and design consequences

### Backend and endpoint are already separate in practice

`backend.mode`, managed-local startup, and backend-startup settings describe
how TOAS provides or manages inference. In contrast, `llm.backends[]` mostly
describes named URLs, credentials, and model hints. The current code therefore
has both concepts, but one of them is named “backend” in the catalog and the
other is named “backend” in runtime policy.

The migration should adapt the current catalog toward endpoint definitions and
retain backend policy for execution/lifecycle semantics. A compatibility reader
or adapter is acceptable during migration; long-term compatibility is not a
design constraint.

### Provider is currently too global

Selecting a named catalog backend changes its URL and model, but the model
invocation path inherits the global provider. A future endpoint definition
should be able to own its provider/protocol, even if the first migration keeps
the global field as a fallback.

### Catalog and selection are currently mixed

`llm.models` is a global static catalog. `llm.backends[].models` is an
endpoint-associated static catalog. `llm.backends[].model` is a default
requested model. `llm.model` is the scalar requested model. These should not
be treated as interchangeable model facts.

### Live discovery and durable catalog refresh are distinct

The existing `fetch_models()` transport can support explicit live observation,
but an observation should not silently rewrite configuration. The intended
lifecycle is:

```text
live observation → explicit catalog refresh → target selection
```

An explicit refresh may add newly observed model IDs and preserve curated
metadata such as labels, tags, and notes. Absence from one response should not
implicitly delete a catalog entry. Probe failure should produce no catalog
write, and refreshing a catalog should never change the active target.

## Emerging operator model

Names remain subject to design, but the semantic roles are expected to be
roughly:

```text
/models              inspect live models from an endpoint
/models known        inspect the durable model catalog
/models refresh      explicitly merge live observations into the catalog
/model targets       inspect durable named targets
/model               show the active target and navigation hints
/model select NAME   select a named target for the session
/endpoints           inspect configured endpoint definitions
```

These are semantic placeholders, not an implementation commitment. In
particular, `/model` and `/models` are high-profile names and should not be
locked to behavior until the target and endpoint vocabulary is stable.

## Target shape

The first target representation should keep generation fields embedded rather
than introducing an independent generation-profile registry prematurely:

```toml
[llm.targets.local-qwen-high]
endpoint = "local"
model = "qwen3.6-26B"

[llm.targets.local-qwen-high.generation]
thinking_mode = "enabled"
thinking_budget_tokens = 1024
```

If later reuse or provider-specific translation justifies named generation
profiles, the target can promote those fields to a profile reference without
changing the target-selection concept.

Target aliases are durable configuration objects subject to the normal
global/project hierarchy. The active target is a session override referring to
one of the effective named targets; target definitions are not session-local
objects.

## Shorthand direction

A parseable shorthand may be useful when declaring aliases, but it should
expand immediately into structured target data. It should not be the canonical
semantic identity of a target, and TOAS should not infer stable meaning from an
arbitrary name such as `qwen3.6-26B-high`.

Conceptually:

```text
parseable declaration → structured named target → target selection
```

This leaves provider-specific differences in structured fields rather than
assuming that “high”, “low”, or “disable-thinking” mean the same thing for
every model and endpoint.

## Migration direction

The likely sequence is:

1. Inventory and map current backend, endpoint, catalog, model, and generation
   fields.
2. Separate endpoint-shaped catalog data from backend lifecycle semantics.
3. Preserve the current scalar configuration as an implicit default endpoint
   and target during migration.
4. Introduce durable named targets with embedded generation fields.
5. Add effective endpoint and target inspection.
6. Add explicit live model observation and explicit catalog refresh.
7. Add `/model select NAME` as a session selection override.
8. Retire compatibility adapters once the new semantic surfaces are proven.

## Open questions

- What is the final public name for endpoint configuration while “backend” is
  retained for execution/lifecycle?
- Which endpoint properties are provider-specific versus shared protocol
  fields?
- Should endpoint-associated known models be stored inside endpoint entries or
  in a separate catalog relation?
- What exact shorthand grammar is worth supporting for alias declaration?
- What is the default write scope for creating a target or endpoint: project,
  global, or an explicit scope argument?
- How should a refresh record last-seen metadata without making observations
  look like configuration truth?

## Deliberate deferrals

- In-process inference implementation and lifecycle details.
- Automatic model selection from live observations.
- A universal help registry or a final command spelling for every inspection
  surface.
- A standalone named generation-profile registry.
