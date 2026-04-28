# 451: /help Tools Defaultable-Argument Metadata And Rendering

## Problem
`/help tools` currently derives argument shape from `Tool.required_args` only, so tools with optional/defaultable arguments are rendered incompletely (for example `code_survey` appears as args `none` even though it supports optional `path` and `top_n` with defaults).

## Goal
Make `/help tools` reliably represent required and optional/defaulted arguments using a single source of truth.

## Scope
- add argument metadata surface for tool definitions (required + optional + default/value-shape notes)
- update `/help tools` rendering to display both required and optional/defaulted arguments
- ensure `code_survey` and other defaultable tools render accurate help text
- add tests that lock help output for tools with optional/defaulted args

## Constraints
- preserve existing callable validation behavior and execution semantics
- avoid duplicating per-tool arg contracts in multiple places
- keep output compact and operator-readable

## Done When
- `/help tools` accurately reflects optional/defaulted arguments for defaultable tools
- tests cover rendering and at least one regression case (`code_survey`)
- roadmap/task stitching reflects landed behavior

## Completion
- added tool-level optional/default argument metadata in `Tool` registry entries
- updated `/help tools` rendering to include optional/default lines
- `code_survey` now explicitly renders optional/default argument shape in help output
- added regression coverage in `tests/test_step.py` for code_survey help rendering
