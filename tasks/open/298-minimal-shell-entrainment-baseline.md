## Goal

Capture a known-good minimal command-lane entrainment pattern as explicit prompt-library material and verify it remains accepted by extraction/step flows.

## Why Now

A tiny user-authored entrainment proved effective in live use:
- single YAML object
- single `command` field
- explicit user-exec/result loop

This is high-leverage behavior and should be stabilized as first-class prompt guidance rather than left as ad-hoc operator folklore.

## Scope

- add a prompt-library artifact (or section in existing capability/session-start material) that presents a minimal shell-command lane contract
- keep format narrowly parseable (single-field YAML command object)
- add tests proving the documented lane shape is recognized and remains compatible with current extraction behavior
- document intended safety boundary text (reasonable/safe/goal-directed user execution)

## Intended Inputs

- prompt assets in `src/toas/prompts/...`
- capability overview rendering in `src/toas/capability_prompts.py`
- extraction behavior in `src/toas/step.py`

## Intended Outputs

- stable prompt-library reference for the minimal command lane
- test coverage for command-lane recognition from this baseline phrasing
- brief docs note linking the baseline to extraction semantics

## Constraints

- do not introduce hidden policy; keep behavior explicit in prompt assets
- do not weaken existing bounded `shell` tool policy semantics
- keep direct user intent lane distinct from model-addressable tool registry lane

## Non-Goals

- no new tool capability
- no redesign of command execution path
- no expansion into multi-field action schemas in this task

## Done When

- baseline entrainment text is discoverable in prompt-library material
- extraction/step tests cover the baseline shape
- docs/prompt comments explain why this lane is intentionally minimal
