## Goal

Add observability for model reasoning-style output (for example `<think>...</think>`) without roundtripping that content into subsequent model-input context.

## Scope

- detect and classify reasoning-style blocks in assistant output
- make reasoning presence visible to the operator in session projection
- prevent reasoning blocks from being fed back into future model-input projection by default
- define optional durable capture behavior tied to trace policy where appropriate

## Intended Inputs

- transcript projection and model-input projection paths
- `llm_call` durability policy work (`238`)
- backend-adaptive generation policy context

## Intended Outputs

- explicit projection/input policy for reasoning-style blocks
- tests covering visible projection and non-roundtripping behavior
- clear docs on default behavior and optional debug capture

## Constraints

- preserve user-visible assistant content integrity outside reasoning-strip policy
- avoid hidden mutation of durable message facts
- keep policy deterministic and inspectable

## Non-Goals

- no attempt to fully parse every provider-specific reasoning format
- no guarantee of complete reasoning-capture fidelity across all backends

## Done When

- operators can observe when reasoning blocks occurred
- future model calls do not silently re-ingest reasoning blocks by default
- interaction with trace mode is explicit and documented
