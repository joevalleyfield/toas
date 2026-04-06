## Goal

Improve discoverability and operator coaching for high-impact generation/runtime config knobs so users can adjust behavior via supported surfaces instead of source edits.

## Why Now

A live workaround hardcoded `extra_body=None` in policy derivation due to uncertainty about available config controls. Existing knobs (`generation.thinking_mode`, retry settings) are functional but insufficiently discoverable in real operation.

## Scope

- improve `/help` and/or `/config` guidance for commonly needed generation keys:
  - `generation.thinking_mode`
  - `generation.max_retries`
  - `generation.retry_delay_s`
- add a "common goals" operator-facing help section that maps intent to exact commands/keys
  - enable/disable thinking
  - adjust retry behavior
  - inspect active overrides
- add concise operator-facing examples for per-session (`/config set ...`) and project (`toas.toml`) usage
- ensure `/config set` error messaging on invalid values references valid options and provides a concrete correction example
- ensure successful `/config set` output reinforces learning:
  - what changed
  - where it applies (session override)
  - how to persist in `toas.toml` and how to revert

## Intended Inputs

- help rendering in `src/toas/step.py`
- config parsing/validation in `src/toas/config.py`
- user docs in `README.md` and/or `docs/roadmap.md`

## Intended Outputs

- clearer built-in discoverability for generation controls
- in-band operator coaching at the point of action (`/help`, `/config show`, `/config set`)
- reduced need for ad-hoc code hacks to alter backend behavior
- tests for help/config output expectations where behavior changed

## Constraints

- keep CLI thin and avoid embedding hidden runtime policy
- preserve existing config key names unless a separate migration task is opened

## Non-Goals

- no new generation policy fields in this task
- no backend transport semantics changes

## Done When

- operators can discover and apply `generation.thinking_mode` from in-product help
- `/help` includes a concise common-goals-to-commands section for generation controls
- invalid `/config set` attempts return actionable correction guidance (valid values + concrete example)
- successful `/config set` responses provide next-step guidance (persist/revert)
- docs include a minimal, correct config workflow
- tests cover updated help/config guidance behavior
