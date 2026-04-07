## Goal

Provide a secret-safe runtime override path for `llm_api_key` that does not persist to transcript, event log, or other durable history.

## Why Now

Operators need in-band control for API keys, but durable `/config set` semantics currently write `config_override` records to history. Secret-bearing values must not be captured there.

## Scope

- define a dedicated secret-setting path (for example `/config secret set llm_api_key <value>` or equivalent) that:
  - updates live runtime state
  - never writes secret values to `events.jsonl`
  - never injects secret text into `session.md` projection/output
- provide a redacted inspect path for secret presence (set/unset) without revealing value
- ensure daemon/RPC flows preserve non-durable handling semantics

## Intended Inputs

- operator command handling in `src/toas/step.py`
- runtime state wiring in `src/toas/cli.py` and daemon/RPC surfaces as needed
- history writers in `src/toas/graph.py`

## Intended Outputs

- secure in-band API-key override workflow
- explicit redaction behavior in outputs/errors/help
- tests proving no secret persistence in logs/transcript/output

## Constraints

- never persist raw secret values to durable records
- never echo raw secret values in result content
- behavior must remain deterministic and explicit (no hidden retroactive mutation)

## Non-Goals

- external secret-manager integration
- encrypting existing durable history retroactively

## Done When

- operator can set/clear `llm_api_key` for current runtime without durable writes
- status output indicates presence without exposing value
- tests assert secrets do not appear in `events.jsonl`, transcript projection, or stdout result content
