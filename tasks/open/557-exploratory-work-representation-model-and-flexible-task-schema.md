# 557 Exploratory Work Representation Model and Flexible Task Schema
keywords: exploration, explore, parked, research, task-schema, representation-model, workboard, structure

## Why
The current task format (`## Objective`, `## Done When`) is too rigid for exploratory work (spikes, research, design) but too flexible for tracked implementation. This creates a tension where exploratory tasks are either under-documented (leading to loss of context) or over-engineered (leading to process overhead).

The "Workboard" and auto-sync scripts assume a linear, verifiable structure. Exploratory work often yields non-linear insights, dead ends, or open-ended questions that don't fit "Done When."

Architecture follow-through has made the same pressure visible from another
angle: active work may be tree- or graph-shaped even when the open-task
inventory is linear. The task schema should support explicit `Parent:`,
`Blocks:`, `Blocked by:`, and `Related:` links before any automation tries to
infer them.

## Goal
Define a flexible task schema that supports both "Verified Implementation" tasks and "Exploratory/Research" tasks without forcing one into the other's mold.

## Scope
- Analyze existing "exploratory" tasks (e.g., `488`, `510`, `550`) to identify common patterns.
- Design a new task template or extension mechanism for exploratory work.
- Preserve explicit tree/graph relationships for active coordination work
  without requiring every task list to become hierarchical.
- Update `sync_workboard.py` to handle the new schema gracefully.
- Propose a "Research Outcome" section to replace "Done When" for exploratory tasks.

## Non-Goals
- Rewriting all existing task files.
- Changing the core git-based workflow.

## Proposed Direction
1. **Add a `Type` field:** `implementation`, `exploration`, `maintenance`.
2. **Conditional Sections:**
   - If `Type: exploration`, require `## Research Questions` and `## Findings` instead of `## Done When`.
   - If `Type: implementation`, require `## Done When` and `## Acceptance Criteria`.
3. **Relationship Fields:** Support optional manual relationship fields such
   as `Parent:`, `Blocks:`, `Blocked by:`, and `Related:`. These fields should
   encode intentional structure; inferred links remain a separate `558`
   concern.
4. **Workboard Integration:**
   - The Workboard should visually distinguish between types (e.g., icons or colors).
   - Exploratory tasks should not be flagged as "Stale" based on git timestamps if they have recent "Findings."
   - Active coordination sections may render a tree, while the generated open
     inventory can remain a flat queue.

## Progress

- 2026-06-14: Added a lightweight relationship-field convention to
  `tasks/README.md` so active planning can be tree/graph-shaped without waiting
  for inferred dependency automation.

## Validation
- Pilot the new schema on one open exploratory task (e.g., `488`).
- Update `sync_workboard.py` to parse the new schema.
- Verify that the Workboard still provides a clear, high-level view.

## Related
- `488` Multi-operator orchestration exploration
- `510` Fenced import blocks (design-heavy)
- `550` Root sentinel taxonomy unification (design-heavy)
