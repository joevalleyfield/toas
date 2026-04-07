## Goal

Make execution-layer ownership explicit and enforce frontier-time continuation behavior for unavailable capabilities, without introducing new capability surfaces yet.

## Why Now

Current behavior is mostly aligned but implicit. We need explicit semantics to avoid least-surprise gaps as transcript-scoped state (env/model/cwd) and operator-scoped baseline config continue to expand.

## Scope

- document and enforce layer split:
  - operator baseline (`/config`): defines capability space and defaults
  - transcript state commands: branchable/replayable intent
  - frontier resolution: capability availability check at consumption time
- standardize frontier failure mode for unavailable capability selection:
  - no hidden fallback
  - emit continuation guidance in-band
- define common continuation shape that can be reused by model/tool/env capability failures

## Intended Inputs

- slash-command semantics in `src/toas/step.py`
- operator/runtime docs in `README.md` and `docs/vision.md`
- frontier consequence formatting patterns in `step.py`

## Intended Outputs

- explicit, durable docs for layer ownership and failure semantics
- consistent frontier continuation UX for unavailable selections
- no silent auto-heal behavior when capability resolution fails

## Constraints

- avoid major feature additions in this task
- preserve existing behavior where already compliant
- keep continuation text concise and actionable

## Non-Goals

- no env modifier command implementation (separate task)
- no model selection surface implementation changes (separate task)
- no prompt command-surface migration (separate task)

## Done When

- docs clearly define operator baseline vs transcript state vs frontier validation
- at least one capability-unavailable path emits explicit continuation guidance instead of hidden fallback
- tests cover continuation shape and non-silent failure behavior
