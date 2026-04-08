## Goal

Improve entrainment and tool advertisement so models emit correct callable shapes on first pass, especially for multi-file update workflows that benefit from multi-operation YAML lists.

## Why Now

Runtime already supports single-call and list-call plans, but models often discover argument names only via error feedback. A small, use-case-oriented prompt + advertisement upgrade can reduce retries and shape drift.

## Scope

- update prompt guidance to be use-case oriented:
  - default to single operation
  - use list form when operations are tightly coupled (for example, coherent multi-file updates)
- add one compact multi-op YAML example with full args (canonical shape)
- touch up tool advertisement/help text to include:
  - required argument names per tool
  - canonical callable shape line per tool
  - explicit alias note (`operation/tool_name`, `arguments/args`)
- keep prompt concise (avoid large templates)

## Intended Inputs

- prompt assets under `src/toas/prompts/protocol/...`
- prompt rendering/capability advertisement paths in `src/toas/prompts.py` and `src/toas/step.py`
- tests for prompt/help content in `tests/test_prompts.py` and `tests/test_step.py`

## Intended Outputs

- clearer first-pass callable output from models
- reduced dependence on runtime error messages for arg discovery
- stable multi-op list usage for multi-file edit workflows

## Constraints

- no runtime parser or execution semantics changes
- avoid expanding prompt verbosity substantially
- preserve existing compatibility aliases and extraction tolerance

## Non-Goals

- no tool policy changes
- no new tool implementations
- no broad prompt-family redesign

## Done When

- prompt includes concise multi-op use-case guidance and one full-args list example
- tool advertisement/help includes required args and canonical shape hints
- tests assert presence of the new guidance/example
- no regressions in existing prompt/extraction behavior tests
