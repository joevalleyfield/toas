Filed as: 260906-named-model-targets
FKA:
AKA: target aliases; composite model selection; named inference targets
Legacy index:

keywords: config, implementation, follow-on, usability, contract, naming, runtime

Parent:
Depends on: `260906-endpoint-backend-separation`
Blocks:
Blocked by: `260906-endpoint-backend-separation`
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

## Next Actions

1. Define the smallest target schema against the endpoint seam.
2. Add config parsing, hierarchy merging, and effective-target resolution.
3. Add resolver tests before choosing final operator command names.
