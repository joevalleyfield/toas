# 452: Compact Default Help With Expandable Detail And Approval Surface

## Problem
The current base `/help` output is too verbose for fast operator orientation, while key operational affordances (especially approval-related command surfaces) are not obvious enough to new users.

## Goal
Provide a compact default help view with explicit expansion paths, and make approval/queue control surfaces discoverable in a concise way.

## Scope
- define a compact default `/help` output focused on high-frequency commands and immediate next actions
- add an expanded help view (for example `/help full` or similar) analogous to prompt-surface expansion patterns
- include a compact approvals/queue help surface (for example dedicated `/help approvals` topic or equivalent)
- ensure the default help points clearly to deeper help surfaces (`commands`, `tools`, `cli`, approvals)
- add tests for default and expanded help rendering paths

## Constraints
- keep base `/help` short enough for routine use
- preserve existing command semantics
- avoid duplicating long-form help text across multiple renderers

## Done When
- default `/help` is materially more compact and action-oriented
- expanded/help-topic paths expose full detail on demand
- approval/queue controls are clearly discoverable from help output
- tests lock expected behavior and output shape

## Completion
- switched default `/help` to compact, action-oriented output
- added `/help full` for expanded full-detail guidance
- added `/help approvals` topic for queue/approval discoverability
- preserved full-detail CLI `run_help` output by using full help renderer
- added/updated tests for compact/full/approvals help paths and outputs
