## Goal

Add backend-alias capability-space management (endpoint-first) with safe secret references, including optional platform-local secret storage via a Python keyring provider.

## Why Now

Model-only selection is too shallow for multi-provider operation. TOAS needs backend-level selection (`endpoint + auth + defaults`) and a safe way to capture/use credentials without leaking secrets into transcript/history/event logs.

## Scope

- add backend alias catalog to config (for example `llm.backends`)
- add transcript selector command for backend intent:
  - `/backend` (list current capability space)
  - `/backend <id>` (set transcript-scoped backend intent)
- preserve transcript-scoped `/model` selection, but resolve model within selected backend domain
- add config mutation commands for backend aliases:
  - add/set/remove/list
  - capture current `TOAS_LLM_*` runtime into backend alias
- add secret reference surfaces for backend auth material:
  - env-var reference baseline
  - optional platform-local secret provider (`keyring`) target
- ensure secrets never appear in durable transcript/history/event payloads

## Intended Behavior

- backend aliases are configuration-defined, not hardcoded
- backend selection is transcript-scoped and branchable, like `/model`
- frontier resolves `(backend, model)` at consumption time
- unavailable backend/model yields explicit continuation guidance
- capture flow can snapshot runtime env-backed endpoint/model into a named backend alias
- secret values are written/read through secret surfaces, not durable cleartext config

## Intended Inputs

- `src/toas/config.py`
- `src/toas/step.py`
- `src/toas/cli.py`
- runtime/LLM selection plumbing
- docs/help surfaces (`README.md`, `/help`, `/config show`)
- tests across config parsing, command behavior, and secrecy guarantees

## Intended Outputs

- endpoint-first selection model for multi-provider workflows
- safer credential handling with local provider support
- clearer split between capability definition (`/config`) and transcript state (`/backend`, `/model`)

## Constraints

- preserve append-only durability semantics
- do not leak secret values to transcript, stdout projections, or `events.jsonl`
- keep backward compatibility for existing single-endpoint config
- keep env-based auth support as fallback even if keyring is unavailable

## Non-Goals

- no mandatory keyring dependency for minimal installs
- no cloud secret manager integration in first pass
- no provider-specific hardcoded backend presets

## Done When

- backend alias catalog is parsed/validated with tests
- `/backend` list/select behavior is implemented with transcript-scoped intent
- frontier model resolution is backend-aware with continuation guidance
- backend mutation/capture commands exist and are tested
- secret references work with env baseline and optional keyring provider
- docs clearly describe endpoint-first selection and secret handling semantics
