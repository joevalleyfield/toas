## Goal

Extend the backend-adaptive generation policy so that behavioral controls are explicit, config-backed, and inspectable — rather than hardcoded in `default_backend_policy()`.

## Why Now

`OperatorConfig` now provides the persistence layer (file config + durable session overrides + `/config` command) that this arc needs. The `BackendGenerationPolicy` object currently hardcodes all its values and bypasses config entirely. Two of its fields are live (`extra_body`, `avoid_terms`); three are aspirational and unconnected. This arc makes the live fields user-facing and retires the vestigial ones cleanly.

## Scope

- `261`: add `GenerationPolicy` section to `OperatorConfig`; wire live fields through config; update consumers
- `262`: audit and retire the three aspirational `BackendGenerationPolicy` fields that are currently stored but never consumed

## Intended Inputs

- `OperatorConfig` and config persistence layer from `250`
- `BackendGenerationPolicy` and `default_backend_policy()` in `backend_policy.py`
- `capability_prompts.py` (direct hardcoded policy consumer)
- `cli.py` (derives policy and passes `extra_body` to generation)

## Intended Outputs

- `OperatorConfig` with a `GenerationPolicy` section covering the live behavioral knobs
- `BackendGenerationPolicy` derived from config rather than hardcoded
- All consumers updated to use config-derived policy
- Aspirational fields removed with clear documentation of the seam they were meant to fill
- Tests covering config round-trip, derivation, and consumer behavior

## Constraints

- Default config must reproduce current hardcoded behavior exactly
- Policy derivation must be deterministic and side-effect-free
- No new behavioral changes beyond making existing behavior config-settable

## Done When

- `261` and `262` are closed
- `/config show` includes generation policy knobs
- `BackendGenerationPolicy` is derived from config, not hardcoded
- Aspirational fields are gone and the seam is documented
