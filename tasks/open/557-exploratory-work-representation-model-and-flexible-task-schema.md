# 557 Exploratory Work Representation Model and Flexible Task Schema

## Why
The current task format (`## Objective`, `## Done When`) is too rigid for exploratory work (spikes, research, design) but too flexible for tracked implementation. This creates a tension where exploratory tasks are either under-documented (leading to loss of context) or over-engineered (leading to process overhead).

The "Workboard" and auto-sync scripts assume a linear, verifiable structure. Exploratory work often yields non-linear insights, dead ends, or open-ended questions that don't fit "Done When."

## Goal
Define a flexible task schema that supports both "Verified Implementation" tasks and "Exploratory/Research" tasks without forcing one into the other's mold.

## Scope
- Analyze existing "exploratory" tasks (e.g., `488`, `510`, `550`) to identify common patterns.
- Design a new task template or extension mechanism for exploratory work.
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
3. **Workboard Integration:**
   - The Workboard should visually distinguish between types (e.g., icons or colors).
   - Exploratory tasks should not be flagged as "Stale" based on git timestamps if they have recent "Findings."

## Validation
- Pilot the new schema on one open exploratory task (e.g., `488`).
- Update `sync_workboard.py` to parse the new schema.
- Verify that the Workboard still provides a clear, high-level view.

## Related
- `488` Multi-operator orchestration exploration
- `510` Fenced import blocks (design-heavy)
- `550` Root sentinel taxonomy unification (design-heavy)
