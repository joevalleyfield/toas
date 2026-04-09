## Goal

Introduce a secret-provider abstraction for backend auth material, with environment-variable references as baseline and optional platform-local keyring support.

## Why Now

Backend alias work needs a safe auth story. TOAS should avoid cleartext durable secret storage while still supporting practical local workflows.

## Scope

- define secret source schema for backend auth references:
  - `env` source (`api_key_env`)
  - optional `keyring` source (`service` + `username` or equivalent ref)
- implement runtime secret resolution used by inference settings
- integrate with `/config secret ...` flows where appropriate
- keep keyring dependency optional and graceful when unavailable

## Intended Behavior

- backend config stores secret references, not secret values
- runtime resolves secret values from configured provider
- missing/unavailable provider yields explicit actionable error
- no secret values appear in transcript/history/event payloads

## Intended Inputs

- `src/toas/config.py`
- `src/toas/cli.py`
- optional new secret-provider module
- docs for config and operational behavior
- tests for provider selection and redaction invariants

## Intended Outputs

- portable and safer credential handling
- clean fallback behavior when platform keyring is not installed
- better alignment with backend alias catalog workflows

## Constraints

- keyring integration must be optional
- env fallback must remain supported
- no secret durability regressions

## Non-Goals

- no cloud secret manager integration in first pass
- no mandatory encrypted local store beyond provider capabilities

## Done When

- secret provider abstraction is implemented and tested
- env and optional keyring paths both work
- failures are explicit and non-leaky
- docs explain setup and fallback behavior clearly
