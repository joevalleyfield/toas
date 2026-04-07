## Goal

Expose LLM runtime endpoint/model selection through supported TOAS config surfaces so operators can avoid env-only setup friction.

## Why Now

Live operation revealed a discoverability/control gap: users can tune generation behavior via `/config`, but endpoint/model selection still requires environment variables only. This creates avoidable mismatch between coached config workflows and actual runtime controls.

## Scope

- add config fields for non-secret LLM runtime settings:
  - base URL (endpoint root)
  - model name
- support file-backed project defaults in `toas.toml`
- support session-level overrides via `/config set` for non-secret LLM runtime fields
- update help/docs to show where runtime settings are sourced and precedence rules

## Intended Inputs

- config model/parsing in `src/toas/config.py`
- runtime wiring in `src/toas/cli.py` and `src/toas/llm.py`
- docs/help in `README.md` and `src/toas/step.py`

## Intended Outputs

- endpoint/model configurable via `toas.toml`
- endpoint/model overridable in-session via `/config set`
- explicit precedence order across env, file config, and session overrides

## Constraints

- preserve backward compatibility with existing env-var workflow
- keep secret material out of durable config override records (handled separately in task `305`)
- keep default behavior unchanged when no new config fields are set

## Non-Goals

- secret API key handling in durable config (explicitly excluded)
- automatic endpoint capability probing

## Done When

- users can set endpoint/model in `toas.toml` and see it applied at runtime
- users can adjust endpoint/model with `/config set` in-session
- docs/help clearly explain source precedence and intended usage
- tests cover parsing, wiring, and precedence behavior
