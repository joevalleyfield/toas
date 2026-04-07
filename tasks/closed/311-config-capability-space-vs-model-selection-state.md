## Goal

Separate model capability definition from model selection state: `/config` defines available model space, while `/model` selects transcript-scoped model intent.

## Why Now

Model endpoint/model fields currently live under config overrides, which feels global and can surprise branch/replay expectations. Selection should follow transcript lineage; capability availability should remain operator baseline.

## Scope

- add `/model` command surface:
  - `/model <name>` sets transcript-scoped model selection intent
  - `/model` lists/selects available models from current capability space
- keep `/config` focused on capability-space defaults (endpoint/root and model inventory source)
- validate model availability at frontier consumption time (inference-required steps only)
- when selected model unavailable, emit continuation guidance:
  - `chosen model unavailable`
  - actionable `/model <available>` suggestions

## Intended Inputs

- slash-command handling and continuation rendering in `src/toas/step.py`
- generation settings resolution in `src/toas/cli.py` / `src/toas/llm.py`
- config structures in `src/toas/config.py`
- help text in `step.py` and durable docs

## Intended Outputs

- clear define-vs-select split (`/config` vs `/model`)
- transcript-branchable model choice state
- frontier-time unavailability handling with guided continuation

## Constraints

- no eager validation of `/model` write-time intent
- no silent fallback to another model when selected model is unavailable
- keep existing env/config compatibility paths during migration

## Non-Goals

- no automatic model quality ranking or policy heuristics
- no provider capability probing beyond current configured availability source

## Done When

- `/model` can set and inspect model selection intent
- inference frontier resolves selected model and fails with guided continuation if unavailable
- branch/replay preserves model intent semantics
- tests cover deferred validation and continuation menu behavior
