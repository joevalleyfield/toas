Filed as: 260906-named-model-targets
FKA:
AKA: target aliases; composite model selection; named inference targets
Legacy index:

keywords: config, implementation, follow-on, usability, contract, naming, runtime

Parent:
Depends on: `260906-endpoint-backend-separation`
Blocks:
Blocked by:
Related: `docs/notes/2026-09-06-endpoints-models-and-targets.md`

# Add Durable Named Model Targets

Represent endpoint/model/generation combinations as durable named targets so
operator selection no longer requires independently juggling `/backend`,
`/model`, and generation settings.

## Current Reality

TOAS has scalar `llm.model`, named backend/endpoint-like entries, global
`generation.*`, and transcript-level `/model NAME` selection. There is no
durable object that joins those choices.

## Desired Reality

A target is a durable configuration object containing an endpoint/backend
reference, requested model ID, and embedded generation settings. The active
target is a session-level reference to an effective named target.

## Gap Analysis

- Selection is split across independent transcript commands.
- Generation settings are global even when the operator conceptually wants a
  model/effort combination.
- Target aliases do not yet participate in global/project configuration
  hierarchy.

## Known Facts / Assumptions / Unknowns

- Confirmed: target definitions should not be session-local objects.
- Confirmed: active selection may be a session override.
- Assumption: generation fields should initially be embedded in targets rather
  than promoted to a separate profile registry.
- Unknown: final shorthand grammar and public command spelling.

## Transformations

- Add the minimum durable target representation and config loading/merging.
- Resolve effective targets through the existing configuration hierarchy.
- Resolve an active target into endpoint/model/generation settings without
  silently probing or changing the endpoint.
- Preserve scalar configuration as the implicit default target during
  migration.

## Evidence

- A target can be defined globally and overridden by a project target with the
  same name.
- Selecting a target changes the session selection only.
- Target resolution keeps endpoint, requested model, and generation settings
  separately inspectable.
- Existing scalar and `/model NAME` behavior remains covered during the
  migration period.

## Open Fronts

- Whether target names are user-defined only or may also be generated.
- The declaration shorthand, if any, for expanding a target alias.
- Whether selection validation is purely static or may optionally inspect
  endpoint availability later.

## Progress Evidence

Closed: the durable named-target arc is complete. Target definitions now use
keyed configuration tables with endpoint/model references and sparse generation
overrides; effective resolution preserves endpoint defaults and conservative
inference; selection is a session-level reference; and the operator surface
supports inspection, static selection, derived naming, catalog promotion, and
explicit endpoint bootstrap. The follow-on slices also separate live model
observation from durable catalog inspection and refresh.

The first target foundation now provides durable `TargetCatalogEntry` values
with endpoint and requested-model references plus sparse overrides of the
existing generation policy. Effective configuration layers merge targets by
name, preserving inherited fields while allowing project values to shadow
global values. Target resolution is read-only and performs no endpoint probe.

Focused result: `359 passed`; Ruff passed. The full escalated run reached
`3150 passed, 3 failed, 12 deselected`, with 100% coverage. The three failures
are unrelated Vim plugin timeouts after writing `session.md`.

Selection commands, target inspection, and shorthand declaration remain open.

The invocation seam now resolves a selected target into endpoint, requested
model, API-key, and sparse generation settings without probing. Unknown
endpoint references fail closed at this seam; public selection remains open.

Target configuration is now canonical as keyed TOML tables under
`[llm.targets.<name>]`; the runtime still normalizes these into immutable
entries with an internal `id` for resolution. Legacy array-shaped target
configuration is no longer the authored form.

Endpoint-owned model defaults are now named `default_model` in the canonical
schema, keeping them distinct from a target's requested `model`. The reader
accepts legacy backend `model` fields during migration, but runtime resolution
uses `default_model`.

Effective resolution now applies conservative non-persisting inference: an
explicit endpoint default wins, a single known endpoint model may supply the
default, and a configured global model may supply it when exactly one endpoint
exists. Ambiguous catalogs remain unresolved rather than choosing arbitrarily;
the selected source is retained in the invocation result.

The first operator-facing selection slice is now present. `/model targets`
lists configured target names with their endpoint, requested model, readiness,
and active-session marker. `/model select NAME` validates a named target and
emits a session-level `target_selection` update; the update is persisted as a
durable event after the current command completes. Invocation resolution reads
that event and gives the selected target precedence over legacy backend/model
fragments, including the target's generation settings. The public spelling is
deliberately provisional while the broader `/model` and `/models` taxonomy is
being designed.

Bare `/model` now provides a compact active-target/navigation view whenever
named targets are configured. Configurations without named targets retain the
legacy available-model listing, keeping the migration surface compatible while
making the target affordance discoverable.

## Next Actions

1. Define the smallest target schema against the endpoint seam. (complete)
2. Add config parsing, hierarchy merging, and effective-target resolution. (complete)
3. Add resolver tests before choosing final operator command names. (complete)
4. Decide the final public target inspection/selection grammar and validation
   behavior. (complete: the current static-validation rule remains in force;
   unresolved endpoint references are not selectable, and selection performs
   no live probe.)

Final verification: the implementation slices were verified by the full
strict suite at 100% coverage, with acceptance coverage for endpoint
authoring, model observation, target promotion, bootstrap, and selection.
