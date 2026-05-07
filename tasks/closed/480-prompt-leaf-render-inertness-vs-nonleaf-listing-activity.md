# 480 Prompt Leaf Render Inertness Vs Nonleaf Listing Activity

## Goal
Fix `/prompt` projection semantics so rendered leaf prompt content is inert by default, while non-leaf `/prompt` listing output remains operator-active/selectable.

## Why
Current behavior is inverted for practical operator flow:
- non-leaf `/prompt <prefix>` listing is inert-wrapped
- leaf `/prompt <leaf_ref>` render is active/executable in subsequent steps

This causes rendered prompt/template content (including schema examples) to be treated as executable intent on the next step, producing noise and unintended tool execution.

## Desired Semantics
- `/prompt` non-leaf listing output:
  - projected as normal active result text (not inert)
  - intended for immediate trimming/selection in control/user turns
- `/prompt` leaf rendered content:
  - projected inert by default
  - safe to stage as prelude/context without accidental callable extraction

## Scope
In scope:
- adjust `/prompt` handler/result metadata and/or projection policy to encode leaf-vs-listing inertness semantics
- add tests covering both paths and one-step follow-on extraction behavior
- update capabilities/docs where `/prompt` behavior is described

Out of scope:
- redesign of general inert policy for unrelated result sources
- broader slash-command output taxonomy changes beyond `/prompt`

## Done When
- non-leaf `/prompt` listing renders without inert wrapping
- leaf `/prompt` render is inert-wrapped (or equivalently protected from executable extraction)
- stepping immediately after leaf render does not execute schema/example placeholders from rendered prompt text
- tests cover regression and enforce behavior

## Status
Closed.

## Completion Notes
- `/prompt` leaf renders now project as inert by default (`transcript_inert: true`).
- `/prompt` non-leaf browse output (`/prompt` top-level, `/prompt <prefix>`, `/prompts`) now projects as active/selectable (`transcript_inert: false`).
- Rendering path now honors explicit `transcript_inert` on result nodes.
- Added regression coverage for:
  - prompt command handler metadata (`transcript_inert` flags),
  - transcript rendering behavior for inert-vs-active result projection,
  - step/runtime expected result node shapes for prompt browsing.

Verification:
- `uv run pytest` (full suite): pass.
